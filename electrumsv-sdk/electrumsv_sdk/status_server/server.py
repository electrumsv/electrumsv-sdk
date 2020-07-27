import curio
import logging
import multiprocessing
import signal

from trinket.proto import Application
from trinket.server import Server

try:
    from .routes import bauble
except ImportError:
    from electrumsv_sdk.status_server.routes import bauble

logger = logging.getLogger("status-server")
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(name)-24s %(message)s',
    level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')


class TrinketServer(Server):
    """overwrites 'serve' method to change 'print' statements to logging instead"""

    async def serve(self, app: Application):
        Goodbye = curio.SignalEvent(signal.SIGINT, signal.SIGTERM)
        await app.notify('startup')
        task = await curio.spawn(self.run, app)
        await self.ready.set()
        logger.debug('Trinket serving on {}:{}'.format(*self.sockaddr))
        await Goodbye.wait()
        logger.debug('Server is shutting down.')
        await app.notify('shutdown')
        logger.debug('Please wait. The remaining tasks are being terminated.')
        await task.cancel()
        self.ready.clear()


class StatusServer(multiprocessing.Process):
    """a simple curio-based pub-sub server that emits notifications for the current status of
    active (or inactive) SDK applications."""

    def __init__(self, status_queue: multiprocessing.Queue):
        super(StatusServer, self).__init__()
        self.status_queue = status_queue
        self.curio_status_queue = None

    def run(self):
        self.logger = logging.getLogger("status-server")
        self.curio_status_queue = curio.UniversalQueue()
        try:
            curio.run(self.main(), with_monitor=True)
        except Exception as e:
            self.logger.exception(e)

    async def main(self):
        server = TrinketServer(host='localhost', port=5000)
        t1 = await curio.spawn(server.serve, bauble)
        t2 = await curio.spawn(self.publish_status_update)
        t3 = await curio.spawn(self.status_queue_waiter())
        await t1.join()
        await t2.join()
        await t3.join()

    async def status_queue_waiter(self):
        """blocks on the multiprocessing queue for receiving status updates"""
        while True:
            status = await curio.run_in_thread(self.status_queue.get)
            await self.curio_status_queue.put(status)

    async def publish_status_update(self):
        """immediately emits the status notification (from the multiprocessing queue) to all
        connected clients."""
        while True:
            for ws in bauble.websockets:
                status = await self.curio_status_queue.get()
                await ws.send(status)
            await curio.sleep(0.01)


if __name__ == '__main__':
    status_queue = multiprocessing.Queue()
    StatusServer(status_queue).start()
    for i in range(100):
        status_queue.put((b"status update!"))
