import argparse
import os
from typing import Any, Dict, Iterable, Optional

from . import constants
from .constants import DEFAULT_HTTP_PORT, NAME_SQLITE, DEFAULT_MAPI_HOST, DEFAULT_MAPI_PORT


MAPI_URI_MAP = {
    constants.REGTEST: "https://127.0.0.1:5051/mapi",
    constants.TESTNET: "https://austecondevserver.app/mapi",
    constants.SCALING_TESTNET: "https://mapi.test.taal.com/mapi",
    constants.MAINNET: "https://merchantapi.taal.com/mapi",
}


class EnvDefault(argparse.Action):
    def __init__(self, option_strings: Iterable[str], dest: str, required=True, default=None,
            **kwargs: Dict[str, Any]) -> None:
        if dest:
            # Linux environment variables are case-sensitive.
            # Windows environment variables are case-insensitive.
            envvar = dest.upper().replace("-", "_")
            if envvar in os.environ:
                default = os.environ[envvar]
        if required and default:
            required = False
        super().__init__(option_strings, dest, default=default, required=required, **kwargs)

    def __call__(self, parser: argparse.ArgumentParser, namespace: argparse.Namespace, values: Any,
            option_string: Optional[str]=None) -> None:
        setattr(namespace, self.dest, values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    extend_parser(parser)
    return parser.parse_args()


def extend_parser(parser: argparse.ArgumentParser) -> argparse.Namespace:
    group = parser.add_argument_group("HTTP server options")
    group.add_argument("--regtest", action="store_true", help="run on regtest")
    group.add_argument("--testnet", action="store_true", help="run on testnet")
    group.add_argument("--scaling-testnet", action="store_true",
        help="run on scaling-testnet")
    group.add_argument("--main", action="store_true", help="run on mainnet")

    group.add_argument("--database", action=EnvDefault, default=NAME_SQLITE, type=str,
        help=f"'{NAME_SQLITE}' or some as yet undefined thing for postgres.")
    group.add_argument("--data-path", action=EnvDefault, type=str,
        help="The path that internal state and data is stored under.")
    group.add_argument("--wwwroot-path", action=EnvDefault, type=str,
        help="The path that web pages and content is served from.")
    group.add_argument("--http-server-port", action=EnvDefault, default=DEFAULT_HTTP_PORT, type=int,
        help="The port that the server listens to for HTTP requests.")
    group.add_argument("--mapi-broadcast", action="store_true",
        help="turn on broadcasting via the merchant api")
    group.add_argument("--mapi-host", action=EnvDefault, default=DEFAULT_MAPI_HOST,
        help="merchant api host")
    group.add_argument("--mapi-port", action=EnvDefault, default=DEFAULT_MAPI_PORT,
        help="merchant api port")


def get_network_choice(config):
    network_options = [config.regtest, config.testnet, config.scaling_testnet, config.main]
    assert len([is_selected for is_selected in network_options if is_selected]) in {0, 1}, \
        "can only select 1 network"
    network_choice = constants.REGTEST
    if config.testnet:
        network_choice = constants.TESTNET
    elif config.scaling_testnet:
        network_choice = constants.SCALING_TESTNET
    elif config.main:
        network_choice = constants.MAINNET
    return network_choice


def get_mapi_uri(network_choice):
    return MAPI_URI_MAP[network_choice]

