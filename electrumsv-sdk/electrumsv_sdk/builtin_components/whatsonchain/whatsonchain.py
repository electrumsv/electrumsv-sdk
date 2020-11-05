import logging
import sys
from typing import Optional

from electrumsv_sdk.components import ComponentOptions, Component
from electrumsv_sdk.utils import get_directory_name, kill_process

from .install import fetch_whatsonchain, generate_run_script, packages_whatsonchain
from .start import check_node_for_woc

DEFAULT_PORT = 3002
RESERVED_PORTS = {DEFAULT_PORT}
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    repo = app_state.global_cli_flags[ComponentOptions.REPO]
    if not repo == "":  # default
        logger.error("ignoring --repo flag for whatsonchain - not applicable.")

    # 1) configure_paths (SEE BELOW)
    app_state.src_dir = app_state.remote_repos_dir.joinpath("woc-explorer")

    # 2) fetch (as needed) (SEE BELOW)
    fetch_whatsonchain(app_state, url="https://github.com/AustEcon/woc-explorer.git", branch='')

    # 3) pip install (or npm install) packages/dependencies (SEE BELOW)
    packages_whatsonchain(app_state)

    # 4) generate run script (SEE BELOW)
    generate_run_script(app_state)


def start(app_state):
    logger.debug(f"Starting whatsonchain explorer...")
    if not check_node_for_woc():
        sys.exit(1)

    script_path = app_state.derive_shell_script_path(COMPONENT_NAME)
    process = app_state.spawn_process(f"{script_path}")
    id = app_state.get_id(COMPONENT_NAME)
    app_state.component_info = Component(id, process.pid, COMPONENT_NAME,
        str(app_state.src_dir), "http://127.0.0.1:3002")


def stop(app_state):
    """some components require graceful shutdown via a REST API or RPC API but most can use the
    generic 'app_state.kill_component()' function to track down the pid and kill the process."""
    app_state.call_for_component_id_or_type(COMPONENT_NAME, callable=kill_process)
    logger.info(f"stopped selected {COMPONENT_NAME} instance(s) (if any)")


def reset(app_state):
    logger.info("resetting the whatsonchain is not applicable")


def status_check(app_state) -> Optional[bool]:
    """
    True -> ComponentState.RUNNING;
    False -> ComponentState.FAILED;
    None -> skip status monitoring updates (e.g. using app's cli interface transiently)
    """
    is_running = app_state.is_component_running_http(
        status_endpoint=app_state.component_info.status_endpoint,
        retries=4, duration=3, timeout=1.0, http_method='get')
    return is_running
