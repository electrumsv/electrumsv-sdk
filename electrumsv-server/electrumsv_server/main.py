from .config import parse_args
from . import server_web


def run() -> None:
    config = parse_args()

    server = server_web.create({})
    server.start(port=config.api_server_port)

