import logging
import os
import sys

from .application import Application
from .config import parse_args
from .exceptions import StartupError
from . import server_web

def run() -> None:
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(name)-24s %(message)s',
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S')

    config = parse_args()
    try:
        app = Application(config)
    except StartupError as e:
        sys.exit(e)

    server = server_web.create(app)
    server.start(port=config.http_server_port)
