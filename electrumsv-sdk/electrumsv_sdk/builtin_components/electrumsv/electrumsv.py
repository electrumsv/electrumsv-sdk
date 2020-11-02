import logging
import os
from pathlib import Path
from typing import Optional, Dict

from electrumsv_sdk.components import ComponentOptions, Component
from electrumsv_sdk.utils import is_remote_repo, get_directory_name, kill_process

from .install import configure_paths, fetch_electrumsv, packages_electrumsv, \
    generate_run_script
from .reset import delete_wallet, create_wallet
from .start import is_offline_cli_mode, wallet_db_exists

DEFAULT_PORT = 9999
RESERVED_PORTS = {DEFAULT_PORT}
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
    generate_run_script(app_state)


def start(app_state):
    logger.debug(f"Starting RegTest electrumsv daemon...")
    os.makedirs(app_state.component_datadir.joinpath("regtest/wallets"), exist_ok=True)

    if is_offline_cli_mode(app_state):
        # 'reset' recurses into here...
        script_path = app_state.derive_shell_script_path(COMPONENT_NAME)
        _process = app_state.spawn_process(f"{script_path}")
        return  # skip the unnecessary status updates

    # If daemon or gui mode continue...
    elif not wallet_db_exists(app_state):
        # reset wallet
        delete_wallet(datadir=app_state.component_datadir, wallet_name='worker1.sqlite')
        create_wallet(app_state, datadir=app_state.component_datadir, wallet_name='worker1.sqlite')
        if wallet_db_exists(app_state):
            generate_run_script(app_state)  # 'reset' mutates shell script
        else:
            logger.exception("wallet db creation failed unexpectedly")

    script_path = app_state.derive_shell_script_path(COMPONENT_NAME)
    process = app_state.spawn_process(f"{script_path}")

    logging_path = app_state.component_datadir.joinpath("logs")
    metadata = {"config": str(app_state.component_datadir.joinpath("regtest/config")),
                "datadir": str(app_state.component_datadir)}

    app_state.component_info = Component(app_state.component_id, process.pid, COMPONENT_NAME,
        str(app_state.component_source_dir), f"http://127.0.0.1:{app_state.component_port}",
        metadata=metadata, logging_path=logging_path)


def stop(app_state):
    """some components require graceful shutdown via a REST API or RPC API but most can use the
    generic 'app_state.kill_component()' function."""
    app_state.call_for_component_id_or_type(COMPONENT_NAME, callable=kill_process)
    logger.info(f"stopped selected {COMPONENT_NAME} instance(s) (if any)")


def reset(app_state):
    def reset_electrumsv(component_dict: Dict):
        logger.debug("Resetting state of RegTest electrumsv server...")
        datadir = Path(component_dict.get('metadata').get("datadir"))
        delete_wallet(datadir=datadir, wallet_name='worker1.sqlite')
        create_wallet(app_state, datadir=datadir, wallet_name='worker1.sqlite')

    app_state.call_for_component_id_or_type(COMPONENT_NAME, callable=reset_electrumsv)
    logger.debug("Reset of RegTest electrumsv wallet completed successfully")


def status_check(app_state) -> Optional[bool]:
    """
    True -> ComponentState.RUNNING;
    False -> ComponentState.FAILED;
    None -> skip status monitoring updates (e.g. using app's cli interface transiently)
    """
    # Offline CLI interface
    if is_offline_cli_mode(app_state):
        return  # returning None indicates that the process was intentionally run transiently

    is_running = app_state.is_component_running_http(
        status_endpoint=app_state.component_info.status_endpoint,
        retries=5, duration=2, timeout=1.0)
    return is_running
