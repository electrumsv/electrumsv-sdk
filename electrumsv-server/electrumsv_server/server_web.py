from functools import partial
import logging
import os
from typing import Optional

from trinket import Request, Response, Trinket
from trinket.extensions import logger
from trinket.http import HTTPError, HTTPStatus

from .application import Application
from .constants import DEFAULT_PAGE


log = logging.getLogger("server-web")


async def api_home(app: Application, _request: Request, filename: Optional[str]=None) -> Response:
    if not filename: filename = DEFAULT_PAGE
    page_path = os.path.realpath(os.path.join(app.wwwroot_path, filename))
    if not page_path.startswith(app.wwwroot_path) or not os.path.exists(page_path):
        raise HTTPError(HTTPStatus.NOT_FOUND, f"<html>Page not found: {filename}</html>")

    with open(page_path, "r") as f:
        return Response.html(f.read())


def create(_app: Application) -> Trinket:
    return logger(Trinket())


def add_web_routes(app: Application, server: Trinket) -> Trinket:
    server.route("/")(partial(api_home, app))
    server.route("/{filename}")(partial(api_home, app))
    return server

