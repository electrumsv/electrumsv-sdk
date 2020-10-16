import logging
import subprocess
import sys

from electrumsv_sdk.components import ComponentOptions, Component, ComponentState
from electrumsv_sdk.utils import is_remote_repo, get_directory_name

from .install import configure_paths, fetch_electrumsv, packages_electrumsv, \
    generate_run_scripts_electrumsv
from .start import esv_check_node_and_electrumx_running, init_electrumsv_wallet_dir

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    repo = app_state.start_options[ComponentOptions.REPO]
    branch = app_state.start_options[ComponentOptions.BRANCH]

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

    # Option (1) Only using offline cli interface to electrumsv
    if len(app_state.component_args) != 0:
        if app_state.component_args[0] in ['create_wallet', 'create_account', '--help']:
            return

    # Option (2) Running daemon or gui proper
    esv_check_node_and_electrumx_running()
    init_electrumsv_wallet_dir(app_state)

    script_path = app_state.derive_shell_script_path(COMPONENT_NAME)
    process = app_state.spawn_process(script_path)
    if is_first_run:
        app_state.resetters.reset_electrumsv_wallet()  # create first-time wallet

        if sys.platform in ("linux", "darwin"):
            subprocess.run(f"pkill -P {process.pid}", shell=True)
        elif sys.platform == "win32":
            subprocess.run(f"taskkill.exe /PID {process.pid} /T /F", check=True)
        return start(app_state, is_first_run=False)

    id = app_state.get_id(COMPONENT_NAME)
    logging_path = app_state.electrumsv_data_dir.joinpath("logs")
    metadata = {"config": str(app_state.electrumsv_data_dir.joinpath("regtest/config")),
                "datadir": str(app_state.electrumsv_data_dir)}

    component = Component(id, process.pid, COMPONENT_NAME,
        str(app_state.electrumsv_dir), "http://127.0.0.1:9999", metadata=metadata,
        logging_path=logging_path)

    is_running = app_state.is_component_running(COMPONENT_NAME,
                                           component.status_endpoint, 5, 2)
    if not is_running:
        component.component_state = ComponentState.Failed
        logger.error("Electrumsv failed to start")
        sys.exit(1)
    else:
        component.component_state = ComponentState.Running
        logger.debug("Electrumsv online")

    app_state.component_store.update_status_file(component)
    app_state.status_monitor_client.update_status(component)
    return process



def stop(app_state):
    pass


def reset(app_state):
    pass


def status_check(app_state):
    pass
