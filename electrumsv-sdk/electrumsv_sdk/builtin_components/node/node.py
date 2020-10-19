import logging
from pathlib import Path
from typing import Optional, Dict

from electrumsv_node import electrumsv_node

from electrumsv_sdk.components import ComponentOptions, Component
from electrumsv_sdk.utils import get_directory_name

from .install import fetch_node, configure_paths

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
    rpcport = app_state.component_port
    p2p_port = app_state.component_p2p_port
    data_path = app_state.component_datadir
    id = app_state.get_id(COMPONENT_NAME)
    process_pid = electrumsv_node.start(data_path=data_path, rpcport=rpcport,
                                        p2p_port=p2p_port, network='regtest')
    logging_path = Path(app_state.component_datadir).joinpath("regtest/bitcoind.log")

    app_state.component_info = Component(id, process_pid, COMPONENT_NAME,
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
    id = app_state.global_cli_flags[ComponentOptions.ID]
    components_state = app_state.component_store.get_status()

    def stop_node(component_dict: Dict):
        rpcport = component_dict.get("metadata").get("rpcport")
        if not rpcport:
            raise Exception("rpcport data not found")
        electrumsv_node.stop(rpcport=rpcport)
        logger.info(f"terminated: {component_dict.get('id')}")

    # stop all running components of: <component_type>
    if not id and app_state.selected_component:
        for component in components_state:
            if component.get("component_type") == app_state.selected_component:
                stop_node(component)

    # stop component according to unique: --id
    if id and not app_state.selected_component:
        for component in components_state:
            if component.get("id") == id:
                stop_node(component)
    logger.info(f"stopped selected {COMPONENT_NAME} instance(s) (if any)")


def reset(app_state):
    # Todo for this + stop() can likely generalise it by passing it a 'callable' (function that
    #  takes one argument (component_name)... and the helper function can do the rest... calling
    #  our custom reset or stop function as appropriate for --id or component_name settings.
    id = app_state.global_cli_flags[ComponentOptions.ID]
    components_state = app_state.component_store.get_status()

    def reset_node(component_dict: Dict):
        rpcport = component_dict.get("metadata").get("rpcport")
        datadir = component_dict.get("metadata").get("datadir")
        if not rpcport:
            raise Exception("rpcport data not found")
        electrumsv_node.reset(data_path=datadir, rpcport=rpcport)
        logger.info(f"terminated: {component_dict.get('id')}")

    # reset all running components of: <component_type>
    if not id and app_state.selected_component:
        for component in components_state:
            if component.get("component_type") == app_state.selected_component:
                reset_node(component)

    # reset component according to unique: --id
    if id and not app_state.selected_component:
        for component in components_state:
            if component.get("id") == id:
                reset_node(component)

    logger.debug("Reset of RegTest bitcoin daemon completed successfully.")


def status_check(app_state) -> Optional[bool]:
    """
    True -> ComponentState.RUNNING;
    False -> ComponentState.FAILED;
    None -> skip status monitoring updates (e.g. using app's cli interface transiently)
    """
    return app_state.node_status_check_result
