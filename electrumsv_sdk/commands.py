"""This defines a set of exposed public methods for using the SDK as a library"""
import logging
from typing import Dict, Optional, Tuple

from .components import ComponentStore
from .app_state import AppState
from .constants import NameSpace
from .controller import Controller
from .utils import call_any_node_rpc

logger = logging.getLogger("commands")
controller = Controller(None)  # app_state is only used for the node entrypoint


def install(component_type: str, repo: str = "", branch: str = "",
        component_id: str = "") -> None:

    arguments = ["", NameSpace.INSTALL]
    if repo:
        arguments.append("--" + repo)
    if branch:
        arguments.append("--" + branch)
    if component_id:
        arguments.append(f"--id={component_id}")

    # Must place component type after install options:
    arguments.append(component_type)
    app_state = AppState(arguments)
    app_state.handle_first_ever_run()
    controller.install(app_state.config)


def _validate_network(network: str, component_type):
    components_with_network_option = {'node', 'electrumx', 'electrumsv'}
    if network != '' and component_type not in components_with_network_option:
        raise ValueError(f"Can only specify 'network' for {components_with_network_option}")

    valid_networks = {'regtest', 'testnet'}
    if network not in valid_networks:
        raise ValueError(f"The only supported networks are: {valid_networks}")


def start(component_type: str, component_args: Tuple[str] = (), repo: str = "",
        branch: str = "", new_instance: bool = False, gui: bool = False,
        mode: str="new-terminal", component_id: str = "", network: str="",
        deterministic_seed: bool=False) -> None:
    """mode: can be 'background', 'new-terminal' or 'inline'
    network: can be 'regtest' or 'testnet' """

    arguments = ["", NameSpace.START]
    if repo:
        arguments.append(f"--repo={repo}")
    if branch:
        arguments.append(f"--branch={branch}")
    if new_instance:
        arguments.append("--new")
    if gui:
        arguments.append("--gui")
    if mode:
        arguments.append(f"--{mode}")
    if component_id:
        arguments.append(f"--id={component_id}")

    if network:  # special case - this was added as a dynamic cli extension for only some plugins
        _validate_network(network, component_type)
        arguments.append(f"--{network}")

    # Special case for electrumsv wallet only
    if deterministic_seed:
        arguments.append(f"--deterministic-seed")

    # Must place component type after start options:
    arguments.append(component_type)
    if component_args:
        arguments.extend(component_args)  # e.g. e.g. access electrumsv's internal CLI

    app_state = AppState(arguments)
    app_state.handle_first_ever_run()
    controller.start(app_state.config)


def stop(component_type: Optional[str]=None, component_id: str = "") -> None:

    arguments = ["", NameSpace.STOP]

    if component_id:
        arguments.append(f"--id={component_id}")

    if component_type:
        arguments.append(component_type)

    app_state = AppState(arguments)
    app_state.handle_first_ever_run()
    controller.stop(app_state.config)


def reset(component_type: Optional[str]=None, component_id: str = "", repo: str = "",
        branch: str = "", deterministic_seed: bool=False) -> None:

    arguments = ["", NameSpace.RESET]
    if repo:
        arguments.append(f"--repo={repo}")
    if branch:
        arguments.append(f"--branch={branch}")
    if component_id:
        arguments.append(f"--id={component_id}")

    # Special case for electrumsv wallet only
    if deterministic_seed:
        arguments.append(f"--deterministic-seed")

    if component_type:
        arguments.append(component_type)

    app_state = AppState(arguments)
    app_state.handle_first_ever_run()
    controller.reset(app_state.config)


def node(method: str, *args: str, node_id: str = 'node1') -> Dict:
    return call_any_node_rpc(method, *args, node_id=node_id)


def status(component_type: str = "", component_id: str = "") -> Dict:
    component_store = ComponentStore()
    status = component_store.get_status(component_type, component_id)
    return status
