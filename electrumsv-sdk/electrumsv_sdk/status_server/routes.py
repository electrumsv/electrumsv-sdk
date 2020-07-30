import logging

logger = logging.getLogger("trinket-routes")


async def get_status(app, request):
    await request.parse_body()
    if request.body == b'stop':
        pass


async def update_status(app, request):
    await request.parse_body()
    app.update_status()


async def unsubscribe(app, request):
    """unsubscribe from status updates"""
    await request.parse_body()
    if request.body == b'stop':
        pass


async def subscribe(app, request, websocket):
    """subscribe for status updates"""
    host = request.socket._socket.getpeername()[0]
    port = request.socket._socket.getpeername()[1]
    logger.debug(f"got websocket connection: host={host}, port={port}")
    msg = await websocket.recv()
    logger.debug(f"websocket client closed connection")
