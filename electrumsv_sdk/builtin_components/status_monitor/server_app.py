#
# This is a rough / basic status monitoring server that can be connected to via a websocket
# in order to get an overview and immediate updates about the status of all running components.
#
import asyncio
import json
import logging
import queue
import threading
import time
from random import random
from typing import Dict, Set

import aiohttp

from aiohttp import web
from aiohttp.web_ws import WebSocketResponse
from filelock import FileLock

from electrumsv_sdk.components import ComponentTypedDict
from electrumsv_sdk.config import Config
from electrumsv_sdk.utils import get_directory_name

# might be running this as __main__

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 56565
PING_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/"
REFRESH_INTERVAL = 1.0

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)
aiohttp_logger = logging.getLogger("aiohttp")
aiohttp_logger.setLevel(logging.WARNING)


class ApplicationState(object):

    def __init__(self) -> None:
        self.config = Config()
        self.file_name = "component_state.json"
        assert self.config.SDK_HOME_DIR is not None
        self.lock_path = self.config.SDK_HOME_DIR / "component_state.json.lock"
        self.component_state_path = self.config.SDK_HOME_DIR / self.file_name


        self.file_lock = FileLock(str(self.lock_path), timeout=5)  # pylint: disable=abstract-class-instantiated
        self.previous_state = self.read_state()  # compare at regularly to detect change
        self.websockets: Set[WebSocketResponse] = set()
        self.websockets_lock: threading.Lock = threading.Lock()

        self.update_thread = threading.Thread(target=self.update_status_thread,
            name='status_thread', daemon=True)
        self.update_thread.start()

        self.push_notification_queue: queue.Queue[ComponentTypedDict] = queue.Queue()
        self.update_thread = threading.Thread(target=self.push_notifications_thread,
            name='status_thread', daemon=True)
        self.update_thread.start()
        self.pong_event = asyncio.Event()

    def get_websockets(self) -> Set[web.WebSocketResponse]:
        with self.websockets_lock:
            return self.websockets

    def remove_websockets(self, ws: web.WebSocketResponse) -> None:
        with self.websockets_lock:
            self.websockets.remove(ws)

    def update_status_thread(self) -> None:
        """periodically checks every REFRESH_INTERVAL seconds the component_state.json file (
        protected by a file lock for multiprocess access). If there are changes in any
        components, it will detect this and push the relevant components to the
        push_notification_queue (and therefore all websockets) and log the change."""

        def log_and_push_change(current_component_state: ComponentTypedDict) -> None:
            logger.debug(
                f"Status change for: "
                f"Component(id={current_component_state['id']}, "
                f"component_type={current_component_state.get('component_type')}, "
                f"component_state={current_component_state.get('component_state')})"
            )
            self.push_notification_queue.put(current_component_state)

        while True:
            current_state = self.read_state()
            if not current_state:
                time.sleep(10)
                logger.debug("there is no state in component_state.json yet...")
                continue

            # status change from previous
            for id in current_state.keys():
                current_component_state: ComponentTypedDict = current_state[id]
                prev_component_state = self.previous_state.get(id)

                # new component (new id)
                if not prev_component_state:
                    log_and_push_change(current_component_state)
                    continue

                # change from previous
                match = current_component_state.get('last_updated') == \
                        prev_component_state.get('last_updated')
                if current_component_state and not match:
                    log_and_push_change(current_component_state)

            self.previous_state = current_state
            time.sleep(REFRESH_INTERVAL)

    def push_notifications_thread(self) -> None:
        """emits the status notification (from the queue) to all connected websockets."""
        while True:
            component = self.push_notification_queue.get()
            if not len(self.get_websockets()):
                continue

            for ws in self.get_websockets():
                logger.debug(
                    f"Publishing status update for component:" f" {component['id']}"
                )
                # in the unlikely event a connection is dropped in the milliseconds between
                # last checking, I think this will swallow the exception which is fine by me...
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(ws.send_str(json.dumps(component)), loop)

    def read_state(self) -> Dict[str, ComponentTypedDict]:
        with self.file_lock:
            with open(self.component_state_path, 'r') as f:
                data = f.read()
                if data:
                    component_state: Dict[str, ComponentTypedDict] = json.loads(data)
                    return component_state
                else:
                    return {}

    async def manual_heartbeat(self, ws: WebSocketResponse, ws_id: int) -> None:
        """It seems that aiohttp's built-in heartbeat functionality has bugs
        https://github.com/aio-libs/aiohttp/issues/2309 - resorting to manual ping/pong
        between client / server...

        Additionally asyncio.wait_for doesn't raise a timeout so this is a workaround..."""
        HEARTBEAT_INTERVAL = 0.2
        WAIT_FOR = 2.0
        while True:
            try:
                await ws.send_str("ping")
                # await asyncio.wait_for(self.pong_event.wait(), timeout=2.0)  # ?asyncio bug?
                await asyncio.sleep(WAIT_FOR)
                if not self.pong_event.is_set():
                    raise ConnectionResetError
            except Exception as e:
                logger.info(f"closing websocket id: {ws_id}")
                self.remove_websockets(ws)
                break
            finally:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
        raise ConnectionResetError

    async def listen_for_close(self, ws: WebSocketResponse) -> None:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                    logger.info("closed websocket")
                if msg.data == 'pong':
                    self.pong_event.set()
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error('ws connection closed with exception %s' %
                             ws.exception())

    # ----- HANDLERS -----#

    async def ping(self, request: web.Request) -> web.Response:
        return web.Response(text="true")

    async def get_status(self, request: web.Request) -> web.Response:
        try:
            component_state = self.read_state()
            return web.Response(text=json.dumps(component_state))
        except Exception as e:
            logger.exception(e)
            payload = {"status": None, "error": str(e)}
            return web.Response(text=json.dumps(payload), status=500)

    async def websocket_handler(self, request: web.Request) -> WebSocketResponse:
        """Client must respond to all 'ping' messages with a 'pong' within <= 2 seconds to stay
        connected."""
        ws = web.WebSocketResponse()
        ws_id = int(random() * 1_000_000_000_000)
        logger.info(f"new websocket connection with allocated id: {ws_id}")
        try:
            await ws.prepare(request)
            self.websockets.add(ws)

            # initial response == same as get_status()
            component_state = self.read_state()
            await ws.send_json(component_state)
            await asyncio.gather(
                self.listen_for_close(ws),
                self.manual_heartbeat(ws, ws_id),
            )
            return ws
        except ConnectionResetError:
            await ws.close()
            return ws


def run_server() -> None:
    logging.basicConfig(level=logging.DEBUG)
    app_state = ApplicationState()

    web_app = web.Application()
    web_app['app_state'] = app_state
    web_app.add_routes([
        web.get("/", web_app['app_state'].ping),
        web.get("/api/get_status", web_app['app_state'].get_status),
        web.get("/ws", web_app['app_state'].websocket_handler),
    ])
    web.run_app(web_app, host=SERVER_HOST, port=SERVER_PORT)


if __name__ == "__main__":
    run_server()

