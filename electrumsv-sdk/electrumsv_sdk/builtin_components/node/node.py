import logging
import os
from pathlib import Path
from typing import Optional, Dict

from electrumsv_node import electrumsv_node

from electrumsv_sdk.components import ComponentOptions, Component
from electrumsv_sdk.utils import get_directory_name

from .install import fetch_node, configure_paths
from . import env

DEFAULT_PORT = 18332
DEFAULT_P2P_PORT_NODE = 18444
RESERVED_PORTS = {DEFAULT_PORT, DEFAULT_P2P_PORT_NODE}
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    """The node component has a pip installer at https://pypi.org/project/electrumsv-node/ and
    only official releases from pypi are supported"""
    repo = app_state.global_cli_flags[ComponentOptions.REPO]
    if not repo == "":  # default
        logger.error("ignoring --repo flag for node - not applicable.")

    configure_paths(app_state)
    # 2) fetch (as needed) - (SEE BELOW)
    fetch_node(app_state)
    # 3) pip install (or npm install) packages/dependencies - (NOT APPLICABLE)
    # 4) generate run script - (NOT APPLICABLE)


def start(app_state):
    extra_params = []
    if env.NODE_RPCALLOWIP:
        extra_params.append(f"-rpcallowip={env.NODE_RPCALLOWIP}")
    if env.NODE_RPCBIND:
        extra_params.append(f"-rpcbind={env.NODE_RPCBIND}")
    if not extra_params:
        extra_params = None

    if env.NODE_PORT:
        app_state.component_port = env.NODE_PORT

    rpcport = app_state.component_port
    p2p_port = app_state.component_p2p_port
    data_path = app_state.component_datadir
    component_id = app_state.component_id

    process_pid = electrumsv_node.start(data_path=data_path, rpcport=rpcport,
        p2p_port=p2p_port, network='regtest', extra_params=extra_params)
    logging_path = Path(app_state.component_datadir).joinpath("regtest/bitcoind.log")

    app_state.component_info = Component(component_id, process_pid, COMPONENT_NAME,
        str(app_state.component_source_dir),
        f"http://rpcuser:rpcpassword@127.0.0.1:{rpcport}",
        logging_path=logging_path,
        metadata={"datadir": str(app_state.component_datadir),
                  "rpcport": rpcport,
                  "p2p_port": p2p_port}
    )
    app_state.node_status_check_result = True


def stop(app_state):
    """The bitcoin node requires graceful shutdown via the RPC API - a good example of why this
    entrypoint is provided for user customizations (rather than always killing the process)."""
    def stop_node(component_dict: Dict):
        rpcport = component_dict.get("metadata").get("rpcport")
        if not rpcport:
            raise Exception("rpcport data not found")
        electrumsv_node.stop(rpcport=rpcport)
        logger.info(f"terminated: {component_dict.get('id')}")

    app_state.call_for_component_id_or_type(COMPONENT_NAME, callable=stop_node)
    logger.info(f"stopped selected {COMPONENT_NAME} instance(s) (if any)")


def reset(app_state):
    # Todo for this + stop() can likely generalise it by passing it a 'callable' (function that
    #  takes one argument (component_name)... and the helper function can do the rest... calling
    #  our custom reset or stop function as appropriate for --id or component_name settings.
    def reset_node(component_dict: Dict):
        rpcport = component_dict.get("metadata").get("rpcport")
        datadir = component_dict.get("metadata").get("datadir")
        if not rpcport:
            raise Exception("rpcport data not found")
        electrumsv_node.reset(data_path=datadir, rpcport=rpcport)
        logger.info(f"terminated: {component_dict.get('id')}")

    app_state.call_for_component_id_or_type(COMPONENT_NAME, callable=reset_node)
    logger.debug("Reset of RegTest bitcoin daemon completed successfully.")


def status_check(app_state) -> Optional[bool]:
    """
    True -> ComponentState.RUNNING;
    False -> ComponentState.FAILED;
    None -> skip status monitoring updates (e.g. using app's cli interface transiently)
    """
    return app_state.node_status_check_result
