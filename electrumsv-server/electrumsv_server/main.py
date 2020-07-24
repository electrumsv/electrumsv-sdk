import logging
import sys

from .application import Application
from .config import parse_args
from .exceptions import StartupError
from . import server_web
from . import apis

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
    apis.add_api_routes(app, server)
    # We add this last because it has top-level wildcards.
    server_web.add_web_routes(app, server)
    server.start(port=config.http_server_port)
