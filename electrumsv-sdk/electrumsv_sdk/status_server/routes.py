import json
import logging

from constants import COMPONENT_STATE_PATH
from trinket import Request, Response

logger = logging.getLogger("trinket-routes")


# /api/status/get_status
async def get_status(app, request):
    component_state = []
    with app.file_lock:
        if COMPONENT_STATE_PATH.exists():
            with open(COMPONENT_STATE_PATH, "r") as f:
                component_state = json.loads(f.read())
    return Response.json(json.dumps(component_state))


# /api/status/update_status
async def update_status(app, request: Request):
    app.update_status(json.loads(request.body))
    payload = {"status": "success", "error": None}
    return Response.json(json.dumps(payload))


# /api/status/unsubscribe
async def unsubscribe(app, request):
    """unsubscribe from status updates"""
    raise NotImplementedError


# /api/status/subscribe
async def subscribe(app, request, websocket):
    """subscribe for status updates"""
    host = request.socket._socket.getpeername()[0]
    port = request.socket._socket.getpeername()[1]
    logger.debug(f"got websocket connection: host={host}, port={port}")
    msg = await websocket.recv()
    logger.debug(f"websocket client closed connection")
