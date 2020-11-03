import logging
import os
import sys
from typing import Optional

from electrumsv_sdk.components import ComponentOptions, Component
from electrumsv_sdk.utils import get_directory_name, kill_process

from .install import download_and_install, create_settings_file, get_run_path

DEFAULT_PORT = 45111
RESERVED_PORTS = {DEFAULT_PORT}
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)

NODE_RPC_PORT = 18332
NODE_RPC_USERNAME = "rpcuser"
NODE_RPC_PASSWORD = "rpcpassword"
NODE_ZMQ_PORT = 28332


def install(app_state):
    data_path = app_state.get_component_datadir(COMPONENT_NAME)
    download_and_install(data_path)
    create_settings_file(data_path, DEFAULT_PORT, NODE_RPC_PORT, NODE_RPC_USERNAME,
        NODE_RPC_PASSWORD, NODE_ZMQ_PORT)


def start(app_state):
    logger.debug(f"Starting Merchant API")

    data_path = app_state.get_component_datadir(COMPONENT_NAME)
    # The primary reason we need this to be the current directory is so that the `settings.conf`
    # file is directly accessible to the MAPI executable (it should look there first).
    os.chdir(data_path)
    # Get the path to the executable file.
    run_path = get_run_path(data_path)
    process = app_state.spawn_process(str(run_path))
    id = app_state.get_id(COMPONENT_NAME)
    app_state.component_info = Component(id, process.pid, COMPONENT_NAME,
        data_path, "???")


def stop(app_state):
    """some components require graceful shutdown via a REST API or RPC API but most can use the
    generic 'app_state.kill_component()' function to track down the pid and kill the process."""
    app_state.call_for_component_id_or_type(COMPONENT_NAME, callable=kill_process)
    logger.info(f"stopped selected {COMPONENT_NAME} instance(s) (if any)")


def reset(app_state):
    logger.info("resetting Merchant API is not applicable")


def status_check(app_state) -> Optional[bool]:
    """
    True -> ComponentState.RUNNING;
    False -> ComponentState.FAILED;
    None -> skip status monitoring updates (e.g. using app's cli interface transiently)
    """
    # is_running = app_state.is_component_running_http(
    #     status_endpoint=app_state.component_info.status_endpoint,
    #     retries=4, duration=3, timeout=1.0, http_method='get')
    return True
