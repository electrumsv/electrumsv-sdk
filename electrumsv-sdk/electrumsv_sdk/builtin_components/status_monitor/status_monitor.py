import logging
import os
import sys

from electrumsv_sdk.components import ComponentOptions, ComponentName, Component, ComponentState
from electrumsv_sdk.constants import ComponentLaunchFailedError
from electrumsv_sdk.utils import get_directory_name

from .install import generate_run_script_status_monitor


DEFAULT_PORT_ELECTRUMX = 51001
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    """this is a locally hosted sub-repo so there is no 'fetch' or 'package' installation steps"""
    repo = app_state.start_options[ComponentOptions.REPO]
    if not repo == "":  # default
        logger.error("ignoring --repo flag for status_monitor - not applicable.")

    # 1) configure_paths - (NOT APPLICABLE)
    # 2) fetch (as needed) - (NOT APPLICABLE)
    # 3) pip install (or npm install) packages/dependencies - (NOT APPLICABLE)
    # 4) generate run script - (SEE BELOW)
    generate_run_script_status_monitor(app_state)


def start(app_state):
    component_name = ComponentName.STATUS_MONITOR
    logger.debug(f"Starting status monitor daemon...")
    try:
        script_path = app_state.derive_shell_script_path(component_name)  # move to app_state
        process = app_state.spawn_process(script_path)
    except ComponentLaunchFailedError:
        log_path = app_state.status_monitor_logging_path
        log_files = os.listdir(log_path)
        log_files.sort(reverse=True)  # get latest log file at index 0
        if len(log_files) != 0:
            logger.debug(f"see {log_path.joinpath(log_files[0])} for details")
        sys.exit(1)

    id = app_state.get_id(component_name)
    component = Component(id, process.pid, component_name,
        str(app_state.status_monitor_dir), "http://127.0.0.1:5000/api/status/get_status")

    # move to utils
    is_running = app_state.is_component_running(component_name, component.status_endpoint, 4, 0.5)
    if not is_running:
        component.component_state = ComponentState.Failed
        logger.error("Status_monitor failed to start")
    else:
        component.component_state = ComponentState.Running
        logger.debug("Status_monitor online")
    app_state.component_store.update_status_file(component)
    return process


def stop(app_state):
    pass


def reset(app_state):
    pass


def status_check(app_state):
    pass
