import logging
from pathlib import Path
from typing import Optional

from electrumsv_node import electrumsv_node

from electrumsv_sdk.components import ComponentOptions, ComponentName, Component
from electrumsv_sdk.utils import get_directory_name

from .install import fetch_node


COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    """The node component has a pip installer at https://pypi.org/project/electrumsv-node/ and
    only official releases from pypi are supported"""
    repo = app_state.global_cli_flags[ComponentOptions.REPO]
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

    app_state.component_info = Component(id, process_pid, component_name,
        electrumsv_node.BITCOIND_PATH,
        f"http://rpcuser:rpcpassword@127.0.0.1:18332", logging_path=logging_path,
        metadata={"datadir": electrumsv_node.DEFAULT_DATA_PATH}
    )


def stop(app_state):
    """The bitcoin node requires graceful shutdown via the RPC API - a good example of why this
    entrypoint is provided for user customizations (rather than always killing the process)."""
    electrumsv_node.stop()


def reset(app_state):
    electrumsv_node.reset()
    logger.debug("Reset of RegTest bitcoin daemon completed successfully.")


def status_check(app_state) -> Optional[bool]:
    """
    True -> ComponentState.Running;
    False -> ComponentState.Failed;
    None -> skip status monitoring updates (e.g. using app's cli interface transiently)
    """
    is_running = electrumsv_node.is_node_running()
    return is_running
