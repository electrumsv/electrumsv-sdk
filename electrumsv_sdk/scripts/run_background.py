"""
This script is used in order to launch a background task whilst retaining the ability to call
process.wait() (blocking the thread) and wrap the process with supervisor logic (thereby
capturing the exit returncode for immediate feedback to the status monitor).
"""
import json
import logging
import os
import sys

from electrumsv_sdk.components import Component
from electrumsv_sdk.constants import LOG_LEVEL
from electrumsv_sdk.utils import spawn_background

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("run-background-script")


def unwrap_and_unescape_text(arg: str) -> str:
    return arg.strip("\'").replace('\\"', '"')


def main() -> None:
    command = unwrap_and_unescape_text(os.environ["SCRIPT_COMMAND"])
    component_info = json.loads(unwrap_and_unescape_text(os.environ["SCRIPT_COMPONENT_INFO"]))
    component_info = Component.from_dict(component_info)
    env_vars = os.environ.copy()

    spawn_background(command, env_vars,
        id=component_info.id, component_name=component_info.component_type,
        src=component_info.location, logfile=component_info.logging_path,
        status_endpoint=component_info.status_endpoint, metadata=component_info.metadata)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("an unexpected exception occurred")
        input("press any key to close...")
