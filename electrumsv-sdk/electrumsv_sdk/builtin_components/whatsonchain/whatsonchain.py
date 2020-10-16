import logging
import sys

from electrumsv_sdk.components import ComponentOptions, ComponentName, Component, ComponentState
from electrumsv_sdk.utils import get_directory_name

from .install import fetch_whatsonchain, generate_run_script_whatsonchain, packages_whatsonchain
from .start import check_node_for_woc

DEFAULT_PORT_WHATSONCHAIN = 3002
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    repo = app_state.global_cli_flags[ComponentOptions.REPO]
    if not repo == "":  # default
        logger.error("ignoring --repo flag for whatsonchain - not applicable.")

    # 1) configure_paths (SEE BELOW)
    app_state.woc_dir = app_state.depends_dir.joinpath("woc-explorer")

    # 2) fetch (as needed) (SEE BELOW)
    fetch_whatsonchain(app_state)

    # 3) pip install (or npm install) packages/dependencies (SEE BELOW)
    packages_whatsonchain(app_state)

    # 4) generate run script (SEE BELOW)
    generate_run_script_whatsonchain(app_state)


def start(app_state):
    component_name = ComponentName.WHATSONCHAIN
    logger.debug(f"Starting whatsonchain daemon...")
    if not check_node_for_woc():
        sys.exit(1)

    script_path = app_state.derive_shell_script_path(component_name)
    process = app_state.spawn_process(script_path)
    id = app_state.get_id(component_name)
    component = Component(id, process.pid, component_name,
        str(app_state.woc_dir), "http://127.0.0.1:3002")
    is_running = app_state.is_component_running(component_name, component.status_endpoint,
                                                4, 3, 1.0)
    if not is_running:
        component.component_state = ComponentState.Failed
        logger.error("woc server failed to start")
        sys.exit(1)
    else:
        component.component_state = ComponentState.Running
        logger.debug("Whatsonchain server online")
    app_state.component_store.update_status_file(component)
    app_state.status_monitor_client.update_status(component)
    return process


def stop(app_state):
    """some components require graceful shutdown via a REST API or RPC API but most can use the
    generic 'app_state.kill_component()' function to track down the pid and kill the process."""
    app_state.kill_component()


def reset(app_state):
    logger.info("resetting the whatsonchain is not applicable")


def status_check(app_state):
    pass
