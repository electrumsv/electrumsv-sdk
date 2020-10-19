import logging
import os
import sys
from typing import Optional

from electrumsv_sdk.components import ComponentOptions, Component
from electrumsv_sdk.constants import ComponentLaunchFailedError
from electrumsv_sdk.utils import get_directory_name

from .install import generate_run_script_status_monitor


DEFAULT_PORT_ELECTRUMX = 51001
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    """this is a locally hosted sub-repo so there is no 'fetch' or 'package' installation steps"""
    repo = app_state.global_cli_flags[ComponentOptions.REPO]
    if not repo == "":  # default
        logger.error("ignoring --repo flag for status_monitor - not applicable.")

    # 1) configure_paths - (NOT APPLICABLE)
    # 2) fetch (as needed) - (NOT APPLICABLE)
    # 3) pip install (or npm install) packages/dependencies - (NOT APPLICABLE)
    # 4) generate run script - (SEE BELOW)
    generate_run_script_status_monitor(app_state)


def start(app_state):
    logger.debug(f"Starting status monitor daemon...")
    try:
        script_path = app_state.derive_shell_script_path(COMPONENT_NAME)  # move to app_state
        process = app_state.spawn_process(script_path)
    except ComponentLaunchFailedError:
        log_path = app_state.status_monitor_logging_path
        log_files = os.listdir(log_path)
        log_files.sort(reverse=True)  # get latest log file at index 0
        if len(log_files) != 0:
            logger.debug(f"see {log_path.joinpath(log_files[0])} for details")
        sys.exit(1)

    id = app_state.get_id(COMPONENT_NAME)
    app_state.component_info = Component(id, process.pid, COMPONENT_NAME,
        str(app_state.status_monitor_dir), "http://127.0.0.1:5000/api/status/get_status")


def stop(app_state):
    """some components require graceful shutdown via a REST API or RPC API but most can use the
    generic 'app_state.kill_component()' function to track down the pid and kill the process."""
    app_state.kill_component()
    logger.info(f"stopped selected {COMPONENT_NAME} instance(s) (if any)")


def reset(app_state):
    logger.info("resetting the status monitor is not supported.")


def status_check(app_state) -> Optional[bool]:
    """
    True -> ComponentState.RUNNING;
    False -> ComponentState.FAILED;
    None -> skip status monitoring updates (e.g. using app's cli interface transiently)
    """
    is_running = app_state.is_component_running_http(
        status_endpoint=app_state.component_info.status_endpoint, retries=4, timeout=0.5)
    return is_running
