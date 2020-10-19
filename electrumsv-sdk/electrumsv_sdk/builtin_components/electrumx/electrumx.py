import asyncio
import logging
import os
import shutil
from typing import Optional

from electrumsv_sdk.components import ComponentOptions, Component
from electrumsv_sdk.utils import is_remote_repo, get_directory_name

from .install import configure_paths, fetch_electrumx, packages_electrumx, \
    generate_run_script
from .start import is_electrumx_running

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    """--repo and --branch flags affect the behaviour of the 'fetch' step"""
    repo = app_state.global_cli_flags[ComponentOptions.REPO]
    branch = app_state.global_cli_flags[ComponentOptions.BRANCH]

    # 1) configure_paths
    configure_paths(app_state, repo, branch)

    # 2) fetch (as needed)
    if is_remote_repo(repo):
        repo = "https://github.com/kyuupichan/electrumx.git"
        fetch_electrumx(app_state, repo, branch)

    # 3) pip install (or npm install) packages/dependencies
    packages_electrumx(app_state, repo, branch)

    # 4) generate run script
    generate_run_script(app_state)


def start(app_state):
    logger.debug(f"Starting RegTest electrumx server...")
    script_path = app_state.derive_shell_script_path(COMPONENT_NAME)
    process = app_state.spawn_process(script_path)
    id = app_state.get_id(COMPONENT_NAME)
    app_state.component_info = Component(id, process.pid, COMPONENT_NAME,
        location=str(app_state.component_source_dir), status_endpoint="http://127.0.0.1:51001",
        metadata={"data_dir": str(app_state.component_data_dir)}, logging_path=None)


def stop(app_state):
    """some components require graceful shutdown via a REST API or RPC API but most can use the
    generic 'app_state.kill_component()' function to track down the pid and kill the process."""
    app_state.kill_component()
    logger.info(f"stopped selected {COMPONENT_NAME} instance(s) (if any)")


def reset(app_state):
    repo = app_state.global_cli_flags[ComponentOptions.REPO]
    branch = app_state.global_cli_flags[ComponentOptions.BRANCH]
    configure_paths(app_state, repo, branch)

    logger.debug("Resetting state of RegTest electrumx server...")
    electrumx_data_dir = app_state.component_data_dir
    if electrumx_data_dir.exists():
        shutil.rmtree(electrumx_data_dir)
        os.mkdir(electrumx_data_dir)
    else:
        os.makedirs(electrumx_data_dir, exist_ok=True)
    logger.debug("Reset of RegTest electrumx server completed successfully.")


def status_check(app_state) -> Optional[bool]:
    """
    True -> ComponentState.RUNNING;
    False -> ComponentState.FAILED;
    None -> skip status monitoring updates (e.g. using app's cli interface transiently)
    """
    is_running = asyncio.run(is_electrumx_running())
    return is_running
