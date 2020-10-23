import logging
import os
from pathlib import Path
from typing import Optional

from electrumsv_sdk.app_state import AppState
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import get_directory_name, kill_process

from .server_app import PING_URL, SERVER_PORT

COMPONENT_NAME = get_directory_name(__file__)
COMPONENT_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = COMPONENT_PATH / "server_app.py"

RESERVED_PORTS = {SERVER_PORT}

logger = logging.getLogger(COMPONENT_NAME)


def install(app_state: AppState) -> None:
    pass


def start(app_state: AppState) -> None:
    id = app_state.get_id(COMPONENT_NAME)
    process = app_state.spawn_process(f"{app_state.python} {SCRIPT_PATH}")
    app_state.component_info = Component(id, process.pid, COMPONENT_NAME,
        COMPONENT_PATH, PING_URL)


def stop(app_state: AppState) -> None:
    logger.debug("Attempting to kill the process if it is even running")
    app_state.call_for_component_id_or_type(COMPONENT_NAME, callable=kill_process)


def reset(app_state: AppState) -> None:
    pass


def status_check(app_state: AppState) -> Optional[bool]:
    """
    True -> ComponentState.RUNNING;
    False -> ComponentState.FAILED;
    None -> skip status monitoring updates (e.g. using app's cli interface transiently)
    """
    is_running = app_state.is_component_running_http(
        status_endpoint=app_state.component_info.status_endpoint,
        retries=5, duration=2, timeout=1.0)
    return is_running
