import pprint
import logging
import signal
import sys
import typing
from typing import List, Optional

from .constants import NameSpace
from .config import CLIInputs
from .components import ComponentStore, ComponentTypedDict
from .sdk_types import SelectedComponent
from .utils import cast_str_int_args_to_int, call_any_node_rpc

logger = logging.getLogger("runners")

if typing.TYPE_CHECKING:
    from .app_state import AppState

if sys.platform in ('linux', 'darwin'):
    # https://stackoverflow.com/questions/3234569/python-popen-waitpid-returns-errno-10-no-child-processes
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, signal.SIG_DFL)
    else:
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)


class Controller:
    """Five main execution pathways (corresponding to 5 cli commands)"""

    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.component_store = ComponentStore()
        self.component_info: Optional[ComponentTypedDict] = None

    def get_relevant_components(self, selected_component: SelectedComponent) \
            -> List[ComponentTypedDict]:
        relevant_components = []
        component_state = self.component_store.get_status()
        for component_dict in component_state.values():
            if component_dict.get('component_type') == selected_component:
                relevant_components.append(component_dict)
        return relevant_components

    def install(self, cli_inputs: CLIInputs) -> None:
        logger.info("Installing component...")
        if cli_inputs.component_id or cli_inputs.selected_component:
            component_module = self.component_store.instantiate_plugin(cli_inputs)
            component_module.install()

        # no args implies start all
        if not cli_inputs.component_id and not cli_inputs.selected_component:
            for component in self.component_store.component_map:
                new_cli_inputs = CLIInputs(
                    selected_component=component,
                    background_flag=cli_inputs.background_flag
                )
                self.install(new_cli_inputs)

    def start(self, cli_inputs: CLIInputs) -> None:
        if cli_inputs.component_id or cli_inputs.selected_component:
            logger.info(f"Starting {cli_inputs.selected_component or cli_inputs.component_id} ...")
            component_module = self.component_store.instantiate_plugin(cli_inputs)
            component_module.start()

        # no args implies start all (default component ids only - e.g. node1, electrumx1 etc.)
        if not cli_inputs.component_id and not cli_inputs.selected_component:
            for component in self.component_store.component_map:
                new_cli_inputs = CLIInputs(
                    selected_component=component,
                    background_flag=cli_inputs.background_flag
                )
                self.start(new_cli_inputs)

    def stop(self, cli_inputs: CLIInputs) -> None:
        """stop all (no args) does not only stop default component ids but all component ids of
        each type - hence the need to hunt them all down."""
        if cli_inputs.component_id:
            component_module = self.component_store.instantiate_plugin(cli_inputs)
            component_module.stop()

        elif cli_inputs.selected_component:
            relevant_components = self.get_relevant_components(cli_inputs.selected_component)
            if relevant_components:
                # dynamic imports of plugin
                for component_dict in relevant_components:
                    component_name = component_dict.get("component_type", "")
                    new_cli_inputs = CLIInputs(
                        selected_component=component_name,
                        background_flag=cli_inputs.background_flag,
                    )
                    component_module = self.component_store.instantiate_plugin(new_cli_inputs)
                    component_module.stop()

        # no args implies stop all - (recursive)
        if not cli_inputs.component_id and not cli_inputs.selected_component:
            for component in sorted(self.component_store.component_map.keys(), reverse=True):
                new_cli_inputs = CLIInputs(
                    selected_component=component,
                    background_flag=cli_inputs.background_flag,
                )
                self.stop(new_cli_inputs)
            logger.info(f"terminated: all")

    def reset(self, cli_inputs: CLIInputs) -> None:
        if cli_inputs.component_id or cli_inputs.selected_component:
            component_module = self.component_store.instantiate_plugin(cli_inputs)
            component_module.reset()

        # no args (no --id or <component_type>) implies reset all (node, electrumx, electrumsv)
        if not cli_inputs.component_id and not cli_inputs.selected_component:
            for component in self.component_store.component_map.keys():
                new_cli_inputs = CLIInputs(
                    selected_component=component,
                    background_flag=cli_inputs.background_flag,
                )
                self.reset(new_cli_inputs)
            logger.info(f"reset: all")

    def node(self, cli_inputs: CLIInputs) -> None:
        """Essentially bitcoin-cli interface to RPC API that works 'out of the box' with minimal
        cli_inputs."""
        node_argparser = self.app_state.argparser.parser_map[NameSpace.NODE]
        cli_options = [str(arg) for arg in cli_inputs.node_args if arg.startswith("--")]
        rpc_args = [str(arg) for arg in cli_inputs.node_args if not arg.startswith("--")]
        rpc_args = cast_str_int_args_to_int(rpc_args)

        parsed_node_options = node_argparser.parse_args(cli_options)
        if not parsed_node_options.id:
            component_id = "node1"  # default node instance to attempt
        else:
            component_id = parsed_node_options.id

        if len(rpc_args) < 1:
            logger.error("RPC method not indicated. Requires at least one argument")
            exit(1)

        result = call_any_node_rpc(rpc_args[0], *rpc_args[1:], node_id=component_id)
        if result:
            logger.info(result["result"])

    def status(self, cli_inputs: CLIInputs) -> None:
        status = self.component_store.get_status(cli_inputs.selected_component,
            cli_inputs.component_id)
        pprint.pprint(status, indent=4)
