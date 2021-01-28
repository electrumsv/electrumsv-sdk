"""
This script is used in order to run servers in newly created terminal windows whilst still retaining
the ability to capture both stdout & logging output to file at the same time
"""
import argparse
import json
import logging

from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import spawn_inline


logger = logging.getLogger("run-inline-script")
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(name)-24s %(message)s',
    level=logging.WARNING, datefmt='%Y-%m-%d %H:%M:%S')
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)


def unwrap_and_unescape_text(arg: str):
    return arg.strip("\'").replace('\\"', '"')


def main():
    top_level_parser = argparse.ArgumentParser()
    top_level_parser.add_argument("--command", type=str, default="",
        help="one contiguous string command (to run a server)")
    top_level_parser.add_argument("--env_vars", type=str, default="",
        help="environment variables in serialized json format")
    top_level_parser.add_argument("--component_info", type=str, default="",
        help="component_info")
    parsed_args = top_level_parser.parse_args()
    command = unwrap_and_unescape_text(parsed_args.command)
    component_info = json.loads(unwrap_and_unescape_text(parsed_args.component_info))
    component_info = Component.from_dict(component_info)

    if parsed_args.env_vars:
        env_vars = json.loads(unwrap_and_unescape_text(parsed_args.env_vars))
    else:
        env_vars = None

    spawn_inline(command, env_vars,
        id=component_info.id, component_name=component_info.component_type,
        src=component_info.location, logfile=component_info.logging_path,
        status_endpoint=component_info.status_endpoint, metadata=component_info.metadata)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("an unexpected exception occurred")
        input("press any key to close...")
