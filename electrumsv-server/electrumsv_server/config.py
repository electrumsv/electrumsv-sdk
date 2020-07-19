import argparse
import os
from typing import Any, Dict, Iterable, Optional

from .constants import DEFAULT_HTTP_PORT, NAME_SQLITE


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
    group.add_argument("--database", action=EnvDefault, default=NAME_SQLITE, type=str,
        help=f"'{NAME_SQLITE}' or some as yet undefined thing for postgres.")
    group.add_argument("--data-path", action=EnvDefault, type=str,
        help="The path that internal state and data is stored under.")
    group.add_argument("--wwwroot-path", action=EnvDefault, type=str,
        help="The path that web pages and content is served from.")
    group.add_argument("--http-server-port", action=EnvDefault, default=DEFAULT_HTTP_PORT, type=int,
        help="The port that the server listens to for HTTP requests.")
