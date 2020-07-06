import argparse
import os
from typing import Any, Dict, Iterable, Optional


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
    group = parser.add_argument_group("API server options")
    group.add_argument("--api-server-port", action=EnvDefault, default=58100, type=int,
        help="The port that the API server listens to HTTP requests.")
