"""
This script is used in order to run servers in newly created terminal windows whilst still retaining
the ability to capture both stdout & logging output to file at the same time
"""
import argparse
import json
from pathlib import Path

from electrumsv_sdk.utils import spawn_inline


def unwrap_and_unescape_text(arg: str):
    return arg.strip("\'")


def main():
    # todo - add formal input validation / exception handling
    top_level_parser = argparse.ArgumentParser()
    top_level_parser.add_argument("--command", type=str, default="",
        help="one contiguous string command (to run a server)")
    top_level_parser.add_argument("--env_vars", type=str, default="",
        help="environment variables in serialized json format")
    top_level_parser.add_argument("--logfile", type=str, default="",
        help="absolute logfile path")
    parsed_args = top_level_parser.parse_args()

    command = unwrap_and_unescape_text(parsed_args.command)

    if parsed_args.env_vars:
        env_vars = json.loads(unwrap_and_unescape_text(parsed_args.env_vars))
    else:
        env_vars = None

    if parsed_args.logfile:
        logfile = Path(unwrap_and_unescape_text(parsed_args.logfile))
    else:
        logfile = None

    spawn_inline(command, env_vars, logfile)


if __name__ == "__main__":
    main()

