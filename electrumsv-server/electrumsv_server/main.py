import os
import sys

from .application import Application
from .config import parse_args
from .exceptions import StartupError
from . import server_web


def run() -> None:
    config = parse_args()
    try:
        app = Application(config)
    except StartupError as e:
        sys.exit(e)

    server = server_web.create(app)
    server.start(port=config.http_server_port)
