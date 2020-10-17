import logging
import subprocess
import sys
from typing import Optional

from electrumsv_sdk.components import ComponentOptions, Component
from electrumsv_sdk.utils import is_remote_repo, get_directory_name

from .install import configure_paths, fetch_electrumsv, packages_electrumsv, \
    generate_run_scripts_electrumsv
from .reset import delete_wallet, create_wallet, cleanup
from .start import esv_check_node_and_electrumx_running, init_electrumsv_wallet_dir, \
    is_offline_cli_mode

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    repo = app_state.global_cli_flags[ComponentOptions.REPO]
    branch = app_state.global_cli_flags[ComponentOptions.BRANCH]

    # 1) configure_paths
    configure_paths(app_state, repo, branch)

    # 2) fetch (as needed)
    if is_remote_repo(repo):
        repo = "https://github.com/electrumsv/electrumsv.git" if repo == "" else repo
        fetch_electrumsv(app_state, repo, branch)

    # 3) pip install (or npm install) packages/dependencies
    packages_electrumsv(app_state, repo, branch)

    # 4) generate run script
    generate_run_scripts_electrumsv(app_state)


def start(app_state, is_first_run=False):
    logger.debug(f"Starting RegTest electrumsv daemon...")

    # Offline CLI interface
    if is_offline_cli_mode(app_state):
        return

    # Daemon or GUI mode
    esv_check_node_and_electrumx_running()
    init_electrumsv_wallet_dir(app_state)

    script_path = app_state.derive_shell_script_path(COMPONENT_NAME)
    process = app_state.spawn_process(script_path)
    if is_first_run:
        reset(app_state)  # create first-time wallet

        if sys.platform in ("linux", "darwin"):
            subprocess.run(f"pkill -P {process.pid}", shell=True)
        elif sys.platform == "win32":
            subprocess.run(f"taskkill.exe /PID {process.pid} /T /F", check=True)
        return start(app_state, is_first_run=False)

    id = app_state.get_id(COMPONENT_NAME)
    logging_path = app_state.component_datadir.joinpath("logs")
    metadata = {"config": str(app_state.component_datadir.joinpath("regtest/config")),
                "datadir": str(app_state.component_datadir)}

    app_state.component_info = Component(id, process.pid, COMPONENT_NAME,
        str(app_state.component_source_dir), "http://127.0.0.1:9999", metadata=metadata,
        logging_path=logging_path)


def stop(app_state):
    """some components require graceful shutdown via a REST API or RPC API but most can use the
    generic 'app_state.kill_component()' function to track down the pid and kill the process."""
    app_state.kill_component()


def reset(app_state):
    repo = app_state.global_cli_flags[ComponentOptions.REPO]
    branch = app_state.global_cli_flags[ComponentOptions.BRANCH]
    configure_paths(app_state, repo, branch)

    id = app_state.global_cli_flags[ComponentOptions.ID]
    logger.debug("Resetting state of RegTest electrumsv server...")
    if id is None:
        logger.warning(f"Note: No --id flag is specified. Therefore the default 'electrumsv1' "
                       f"instance will be reset ({app_state.component_datadir}).")
    delete_wallet(app_state)
    create_wallet(app_state)
    cleanup(app_state)
    logger.debug("Reset of RegTest electrumsv wallet completed successfully")


def status_check(app_state) -> Optional[bool]:
    """
    True -> ComponentState.Running;
    False -> ComponentState.Failed;
    None -> skip status monitoring updates (e.g. using app's cli interface transiently)
    """
    # Offline CLI interface
    if is_offline_cli_mode(app_state):
        return  # returning None indicates that the process was intentionally run transiently

    is_running = app_state.is_component_running_http(
        status_endpoint=app_state.component_info.status_endpoint,
        retries=5, duration=2, timeout=1.0)
    return is_running
