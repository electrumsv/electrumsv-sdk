import asyncio
import logging
import requests
import aiohttp

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 56565
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
WS_URL = BASE_URL + '/ws'
GET_STATUS_URL = BASE_URL + '/api/get_status'


class StatusMonitorClient:
    def __init__(self, app_state):
        self.app_state = app_state
        self.logger = logging.getLogger("status-monitor")

    def get_status(self):
        try:
            result = requests.get(GET_STATUS_URL, timeout=5.0)
            result.raise_for_status()
            if result.text:
                return result.json()
        except requests.exceptions.ConnectionError as e:
            self.logger.error("Problem fetching status: reason: " + str(e))
            return False

    async def subscribe(self):
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WS_URL) as ws:
                async for msg in ws:
                    if msg.data == 'ping':
                        await ws.send_str('pong')
                        continue

                    print('Message received from server:', msg)
                    if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break


class MockApplicationState:

    def __init__(self):
        # some state
        pass


# entrypoint to main event loop
async def main():
    app_state = MockApplicationState()
    client = StatusMonitorClient(app_state)
    client.get_status()  # using requests
    await client.subscribe()  # using aiohttp


if __name__ == "__main__":
    asyncio.run(main())
