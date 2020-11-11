import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Dict

from electrumsv_sdk.components import ComponentOptions, Component
from electrumsv_sdk.utils import is_remote_repo, get_directory_name, kill_process, is_docker

from .install import configure_paths, fetch_electrumx, packages_electrumx, \
    generate_run_script
from .start import is_electrumx_running


DEFAULT_PORT = 51001
RESERVED_PORTS = {DEFAULT_PORT}
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
    # temporary docker workaround - the SDK should allow launching components in current terminal
    if is_docker():
        process = app_state.run_command_current_shell(script_path)
    else:
        process = app_state.spawn_process(f"{script_path}")

    app_state.component_info = Component(app_state.component_id, process.pid, COMPONENT_NAME,
        location=str(app_state.component_source_dir), status_endpoint="http://127.0.0.1:51001",
        metadata={"datadir": str(app_state.component_datadir)}, logging_path=None)


def stop(app_state):
    """some components require graceful shutdown via a REST API or RPC API but most can use the
    generic 'app_state.kill_component()' function to track down the pid and kill the process."""
    app_state.call_for_component_id_or_type(COMPONENT_NAME, callable=kill_process)
    logger.info(f"stopped selected {COMPONENT_NAME} instance(s) (if any)")


def reset(app_state):
    def reset_electrumx(component_dict: Dict):
        logger.debug("Resetting state of RegTest electrumx server...")
        datadir = Path(component_dict.get('metadata').get("datadir"))
        if datadir.exists():
            shutil.rmtree(datadir)
            os.mkdir(datadir)
        else:
            os.makedirs(datadir, exist_ok=True)
        logger.debug("Reset of RegTest electrumx server completed successfully.")

    app_state.call_for_component_id_or_type(COMPONENT_NAME, callable=reset_electrumx)
    logger.debug("Reset of RegTest electrumx completed successfully")


def status_check(app_state) -> Optional[bool]:
    """
    True -> ComponentState.RUNNING;
    False -> ComponentState.FAILED;
    None -> skip status monitoring updates (e.g. using app's cli interface transiently)
    """
    is_running = asyncio.run(is_electrumx_running(app_state))
    return is_running
