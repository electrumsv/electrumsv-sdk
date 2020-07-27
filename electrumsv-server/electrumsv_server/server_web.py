from functools import partial
import logging
import mimetypes
import os
from typing import Optional

from trinket import Request, Trinket
from trinket.extensions import logger
from trinket.http import HTTPError, HTTPStatus
from trinket.response import file_iterator, Response

from .application import Application
from .constants import DEFAULT_PAGE


log = logging.getLogger("server-web")


def create(_app: Application) -> Trinket:
    return logger(Trinket())


async def serve_file(app: Application, request: Request, filename: Optional[str]=None) -> Response:
    filepath = request.path[1:].split("/")
    if filepath == [ "" ]:
        filepath = [ DEFAULT_PAGE ]
    page_path = os.path.realpath(os.path.join(app.wwwroot_path, *filepath))
    if not page_path.startswith(app.wwwroot_path) or not os.path.exists(page_path):
        print("..... filename %r", page_path)
        raise HTTPError(HTTPStatus.NOT_FOUND, f"<html>Page not found: {filepath}</html>")

    content_type, encoding_name = mimetypes.guess_type(filepath[-1])
    return Response.streamer(file_iterator(page_path), content_type)


def add_web_routes(app: Application, server: Trinket) -> Trinket:
    server.route("/")(partial(serve_file, app))

    web_paths = []
    for root_path, dirnames, filenames in os.walk(app.wwwroot_path):
        if len(filenames):
            web_path = os.path.relpath(root_path, app.wwwroot_path).replace(os.path.sep, "/")
            web_paths.append(web_path)

    # Deeper paths need to be routed first so as to not override shallower paths.
    for web_path in sorted(web_paths, key=len, reverse=True):
        if web_path == ".":
            server.route("/{filename}")(partial(serve_file, app))
        else:
            server.route("/"+ web_path +"/{filename}")(partial(serve_file, app))
    return server

