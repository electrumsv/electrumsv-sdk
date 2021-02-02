# Adapted from https://stackoverflow.com/questions/48695294/how-can-i-detect-the-closure-of-an-python-aiohttp-web-socket-on-the-server-when
# while looking at ways to handle the issue of when the client exits uncleanly
import logging

import aiohttp
from aiohttp import web
import uuid


class WSClient(object):

    def __init__(self, ws_id: str, websocket: web.WebSocketResponse):
        self.ws_id = ws_id
        self.websocket = websocket


class TxStateWebSocket(web.View):
    """
    This is for notifying the front end that an invoice is now status 'PAID' (enum val of 2)
    """
    logger = logging.getLogger("tx-state-websocket")

    async def get(self):
        ws_id = str(uuid.uuid4())
        try:
            ws = web.WebSocketResponse()
            await ws.prepare(self.request)
            client = WSClient(ws_id=ws_id, websocket=ws)
            self.request.app['ws_clients'][client.ws_id] = client
            self.logger.debug('%s connected. host=%s.', client.ws_id, self.request.host)

            await self.listen(ws_id)

            return ws
        except Exception as e:
            self.logger.exception(f"unexpected websocket exception for: {ws_id}")
            raise
        finally:
            await ws.close()
            self.logger.debug("deleting %s registration", ws_id)
            del self.request.app['ws_clients'][ws_id]

    async def listen(self, ws_id):
        """Currently no messages are expected from the client"""
        client = self.request.app['ws_clients'][ws_id]

        async for msg in client.websocket:
            msg: web.WSMsgType
            if msg.type == aiohttp.WSMsgType.text:
                self.logger.debug('%s client sent: %s', client.ws_id, msg.data)

            elif msg.type == aiohttp.WSMsgType.error:
                # 'client.websocket.exception()' merely returns ClientWebSocketResponse._exception
                # without a traceback. see aiohttp.ws_client.py:receive for details.
                self.logger.error('ws connection closed with exception %s',
                    client.websocket.exception())
