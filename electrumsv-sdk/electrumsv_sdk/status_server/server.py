import json
import os
import sys
import time
from functools import partial
from pathlib import Path
from typing import Optional

import curio
import logging
import logging.handlers
import signal

from constants import FILE_LOCK_PATH  # pylint: disable=E0611
from curio.monitor import Monitor
from filelock import FileLock
from trinket import Trinket
from trinket.proto import Application
from trinket.server import Server

import routes
from logs import trinket_logging_setup

logger = logging.getLogger("status-server")
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)

datadir = None
if sys.platform == "win32":
    datadir = Path(os.environ.get("LOCALAPPDATA")) / "ElectrumSV-SDK"
if datadir is None:
    datadir = Path.home() / ".electrumsv-sdk"

logging_path = datadir.joinpath("logs").joinpath("status_monitor")
os.makedirs(logging_path, exist_ok=True)
logging_filename = str(int(time.time())) + ".log"

root = logging.getLogger()
handler = logging.FileHandler(filename=str(logging_path.joinpath(logging_filename)),
                              mode='a')
formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)-24s %(message)s",
                              datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
root.setLevel(logging.DEBUG)
logging.root.addHandler(handler)
logging.root.addHandler(logging.StreamHandler())


class ServerRunner(Server):
    """overwrites 'serve' method to change 'print' statements to logging instead"""

    async def serve(self, app: Application):
        Goodbye = curio.SignalEvent(signal.SIGINT, signal.SIGTERM)
        await app.notify("startup")
        task = await curio.spawn(self.run, app)
        await self.ready.set()
        logger.debug("Trinket serving on {}:{}".format(*self.sockaddr))
        await Goodbye.wait()
        logger.debug("Server is shutting down.")
        await app.notify("shutdown")
        logger.debug("Please wait. The remaining tasks are being terminated.")
        await task.cancel()
        self.ready.clear()


class StatusServer:
    """a simple curio-based pub-sub server that emits notifications for the current status of
    active (or inactive) SDK applications."""

    def __init__(self):
        super(StatusServer, self).__init__()
        self.file_lock = FileLock(FILE_LOCK_PATH, timeout=1)
        self.curio_status_queue: Optional[curio.UniversalQueue] = None
        self.intentional_task_cancellation = False
        self.kernel = curio.Kernel(debug=False)
        m = Monitor(self.kernel)
        self.kernel._call_at_shutdown(m.close)

    def run(self):
        self.logger = logging.getLogger("status-server")
        try:
            with self.kernel as kernel:
                kernel.run(self.main)
            logger.debug("Status server stopped")
        except Exception as e:
            self.logger.exception(e)

    async def main(self):
        self.curio_status_queue = curio.UniversalQueue()
        Goodbye = curio.SignalEvent(signal.SIGINT, signal.SIGTERM)
        self.server = trinket_logging_setup(Trinket())
        self.add_api_routes(self.server)
        server = ServerRunner(host="localhost", port=5000)
        _tasks = [
            await curio.spawn(server.serve, self.server),
            await curio.spawn(self.publish_status_update),
        ]
        await Goodbye.wait()

    def add_api_routes(self, server: Trinket) -> Trinket:
        """add routes such that application state is accessable in context of handlers"""
        server.route("/api/status/get_status")(partial(routes.get_status, self))
        server.route("/api/status/update_status", ["POST"])(partial(routes.update_status, self))
        server.route("/api/status/unsubscribe", ["POST"])(partial(routes.unsubscribe, self))

        server.websocket("/api/status/subscribe")(partial(routes.subscribe, self))
        return server

    async def publish_status_update(self):
        """immediately emits the status notification (from the multiprocessing queue) to all
        connected clients."""
        while True:
            if len(self.server.websockets):
                for ws in self.server.websockets:
                    component = await self.curio_status_queue.get()
                    self.logger.debug(
                        f"Publishing status update for component:" f" {component['id']}"
                    )
                    await ws.send(json.dumps(component))
            else:  # drain queue
                _component = await self.curio_status_queue.get()
            await curio.sleep(0.2)

    def update_status(self, component):
        self.curio_status_queue.put(component)
        logger.debug(f"Got status update for component: {component['id']}")


if __name__ == "__main__":
    status_server = StatusServer()
    status_server.run()
