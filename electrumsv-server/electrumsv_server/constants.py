from enum import IntEnum

DEFAULT_MAPI_HOST = "127.0.0.1"
DEFAULT_MAPI_PORT = 5051

DEFAULT_HTTP_PORT = 24242
DEFAULT_PAGE = "index.html"

NAME_SQLITE = "sqlite"

XPUB_PATH = "m/0"
XPUB_TEST = "tpubD6NzVbkrYhZ4YdpDXynhCjrA3x9PpW565QX9wLBzqMNX47nixTA7Vzd4yEtWj4FnVzjKbuRbMdLdt6H" \
    "6Q67Qwc7upugtiFxrLgCZbTuLJ7k"


class RequestState(IntEnum):
    UNKNOWN = 0
    UNPAID = 1
    PAID = 2
    CLOSED = 3


REGTEST = "regtest"
TESTNET = "testnet"
SCALING_TESTNET = "scaling_testnet"
MAINNET = "main"
