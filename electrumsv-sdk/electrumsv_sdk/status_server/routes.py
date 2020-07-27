import logging

from electrumsv_sdk.status_server.logs import trinket_logging_setup
from trinket import Trinket

bauble = trinket_logging_setup(Trinket())
logger = logging.getLogger("trinket-routes")

@bauble.websocket('/websocket')
async def serve_websocket(request, websocket):
    host = request.socket._socket.getpeername()[0]
    port = request.socket._socket.getpeername()[1]
    logger.debug(f"got websocket connection: host={host}, port={port}")
    msg = await websocket.recv()
    logger.debug(f"websocket client closed connection")
