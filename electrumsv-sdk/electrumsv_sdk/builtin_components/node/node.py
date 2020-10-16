import logging
from pathlib import Path

from electrumsv_node import electrumsv_node

from electrumsv_sdk.components import ComponentOptions, ComponentName, Component, ComponentState
from electrumsv_sdk.utils import get_directory_name

from .install import fetch_node


COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    """The node component has a pip installer at https://pypi.org/project/electrumsv-node/ and
    only official releases from pypi are supported"""
    repo = app_state.start_options[ComponentOptions.REPO]
    if not repo == "":  # default
        logger.error("ignoring --repo flag for node - not applicable.")

    # 1) configure_paths - (NOT APPLICABLE)  # Todo - need to add this
    # 2) fetch (as needed) - (SEE BELOW)
    fetch_node(app_state)
    # 3) pip install (or npm install) packages/dependencies - (NOT APPLICABLE)
    # 4) generate run script - (NOT APPLICABLE)


def start(app_state):
    component_name = ComponentName.NODE
    process_pid = electrumsv_node.start()
    id = app_state.get_id(component_name)
    logging_path = Path(electrumsv_node.DEFAULT_DATA_PATH)\
        .joinpath("regtest").joinpath("bitcoind.log")

    component = Component(id, process_pid, component_name, electrumsv_node.BITCOIND_PATH,
        f"http://rpcuser:rpcpassword@127.0.0.1:18332", logging_path=logging_path,
        metadata={"datadir": electrumsv_node.DEFAULT_DATA_PATH}
    )
    if not electrumsv_node.is_node_running():
        component.component_state = ComponentState.Failed
        logger.error("bitcoin daemon failed to start")
    else:
        component.component_state = ComponentState.Running
        logger.debug("Bitcoin daemon online")

    app_state.component_store.update_status_file(component)
    app_state.status_monitor_client.update_status(component)

    # process handle not returned because node is stopped via rpc


def stop(app_state):
    """The bitcoin node requires graceful shutdown via the RPC API - a good example of why this
    entrypoint is provided for user customizations (rather than always killing the process)."""
    electrumsv_node.stop()


def reset(app_state):
    pass


def status_check(app_state):
    pass
