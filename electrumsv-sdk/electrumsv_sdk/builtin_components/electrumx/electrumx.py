import asyncio
import logging
import time

from electrumsv_sdk.components import ComponentOptions, ComponentName, Component, ComponentState
from electrumsv_sdk.utils import is_remote_repo, get_directory_name

from .install import configure_paths, fetch_electrumx, packages_electrumx, \
    generate_run_script_electrumx
from .start import is_electrumx_running

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    """--repo and --branch flags affect the behaviour of the 'fetch' step"""
    repo = app_state.start_options[ComponentOptions.REPO]
    branch = app_state.start_options[ComponentOptions.BRANCH]

    # 1) configure_paths
    configure_paths(app_state, repo, branch)

    # 2) fetch (as needed)
    if is_remote_repo(repo):
        repo = "https://github.com/kyuupichan/electrumx.git"
        fetch_electrumx(app_state, repo, branch)

    # 3) pip install (or npm install) packages/dependencies
    packages_electrumx(app_state, repo, branch)

    # 4) generate run script
    generate_run_script_electrumx(app_state)


def start(app_state):
    component_name = ComponentName.ELECTRUMX
    logger.debug(f"Starting RegTest electrumx server...")
    script_path = app_state.derive_shell_script_path(ComponentName.ELECTRUMX)
    process = app_state.spawn_process(script_path)
    id = app_state.get_id(component_name)
    component = Component(id, process.pid, ComponentName.ELECTRUMX,
        location=str(app_state.electrumx_dir),
        status_endpoint="http://127.0.0.1:51001",
        metadata={"data_dir": str(app_state.electrumx_data_dir)},
        logging_path=None,
    )

    is_running = asyncio.run(is_electrumx_running())
    if not is_running:
        component.component_state = ComponentState.Failed
        logger.error("Electrumx server failed to start")
    else:
        component.component_state = ComponentState.Running
        logger.debug("Electrumx online")
    time.sleep(3)
    app_state.component_store.update_status_file(component)
    app_state.status_monitor_client.update_status(component)
    return process


def stop(app_state):
    """some components require graceful shutdown via a REST API or RPC API but most can use the
    generic 'app_state.kill_component()' function to track down the pid and kill the process."""
    app_state.kill_component()


def reset(app_state):
    pass


def status_check(app_state):
    pass
