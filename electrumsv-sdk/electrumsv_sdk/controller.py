import pprint
import logging
from types import ModuleType
from typing import Optional, List

from electrumsv_node import electrumsv_node

from electrumsv_sdk.components import ComponentStore, ComponentOptions, \
    ComponentState, Component

from .handlers import Handlers
from .utils import cast_str_int_args_to_int

logger = logging.getLogger("runners")


class Controller:
    """Five main execution pathways (corresponding to 5 cli commands)"""

    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.handlers = Handlers(self.app_state)
        self.component_store = ComponentStore(self.app_state)

    def get_relevant_components(self, component_id: Optional[str]=None,
            selected_component: Optional[str]=None) -> List[dict]:
        relevant_components = []
        if component_id:
            component_dict = \
                self.app_state.component_store.component_status_data_by_id(component_id)
            if component_dict:
                relevant_components.append(component_dict)

        elif selected_component:
            component_state = self.app_state.component_store.get_status()
            for component_dict in component_state.values():
                if component_dict.get('component_type') == selected_component:
                    relevant_components.append(component_dict)
        return relevant_components

    def start(self, selected_component: Optional[str]=None, repo: str="", component_id: str="",
              background: bool=False, component_args: Optional[List]=None) -> None:

        # Todo beware: global_cli_flags can mutate globally. I think it should change to a named
        #  tuple and passed into the module entrypoints.

        logger.info("Starting component...")
        if background:
            self.app_state.global_cli_flags[ComponentOptions.BACKGROUND] = background
        if repo:
            self.app_state.global_cli_flags[ComponentOptions.REPO] = repo
        if component_id:
            self.app_state.global_cli_flags[ComponentOptions.ID] = component_id
        self.app_state.component_args = component_args
        selected_component = selected_component if selected_component else \
            self.app_state.selected_component

        if component_id or selected_component:
            # global_cli_flags component_id (if any) is retrieved from global state
            if component_id:
                component_dict = \
                    self.app_state.component_store.component_status_data_by_id(component_id)
                component_type = component_dict.get("component_type")
                component_module = self.app_state.import_plugin_component(component_type)
            else:
                component_module = self.app_state.import_plugin_component(selected_component)
            component_module.install(self.app_state)
            component_module.start(self.app_state)
            self.status_check(component_module)

        self.app_state.save_repo_paths()

        # no args implies start all
        if not selected_component:
            for component in self.app_state.component_map:
                self.start(selected_component=component, background=background)

    def stop(self, selected_component: str=None, component_id: Optional[str]="",
            background: bool=True) -> None:
        """if stop_set is empty, all processes terminate."""
        self.app_state.global_cli_flags[ComponentOptions.BACKGROUND] = background
        if component_id:
            self.app_state.global_cli_flags[ComponentOptions.ID] = component_id

        selected_component = selected_component if selected_component else \
            self.app_state.selected_component

        relevant_components = self.get_relevant_components(component_id, selected_component)
        if relevant_components:
            # dynamic imports of plugin
            for component_dict in relevant_components:
                component_name = component_dict.get("component_type")
                component_module = self.app_state.import_plugin_component(component_name)
                component_module.stop(self.app_state)
                component_obj = Component.from_dict(component_dict)
                component_obj.component_state = ComponentState.STOPPED
                self.app_state.component_store.update_status_file(component_obj)

        # no args implies stop all - (recursive)
        if not component_id and not selected_component:
            for component_type in sorted(self.app_state.component_map.keys(), reverse=True):
                self.stop(selected_component=component_type, component_id="")
            logger.info(f"terminated: all")

    def reset(self, selected_component: str=None, component_id: str="", background: bool=True) \
            -> None:
        self.app_state.global_cli_flags[ComponentOptions.BACKGROUND] = background

        selected_component = selected_component if selected_component else \
            self.app_state.selected_component
        component_id = component_id if component_id else \
            self.app_state.global_cli_flags[ComponentOptions.ID]

        # reset by --id flag or by <component_type>
        if selected_component:
            # some components will not have a datadir if they've never been started before but
            # it is the responsibility of the plugin to handle this
            component_module = self.app_state.import_plugin_component(selected_component)
            component_module.reset(self.app_state)

        elif component_id:
            component_dict = self.app_state.component_store.component_status_data_by_id(
                component_id)
            component_name = component_dict.get("component_type")
            component_module = self.app_state.import_plugin_component(component_name)
            component_module.reset(self.app_state)

        # no args (no --id or <component_type>) implies reset all (node, electrumx, electrumsv)
        if not component_id and not selected_component:
            for component_type in self.app_state.component_map.keys():
                self.reset(selected_component=component_type, component_id="")
            logger.info(f"reset: all")

    def status_check(self, component_module: ModuleType):
        """The 'status_check()' entrypoint of the plugin must always run after the start()
        command.

        'status_check()' should return None, True or False (usually in response to polling for an
        http 200 OK response or 4XX/5XX error. However alternative litmus tests are customizable
        via the plugin.

        None type indicates that it was only run transiently (e.g. ElectrumSV's offline CLI mode)

        The status_monitor subsequently is updated with the status."""
        component_id = self.app_state.global_cli_flags[ComponentOptions.ID]
        component_name = component_module.COMPONENT_NAME

        # if --id flag or <component_type> are set and the
        if component_id != "" or component_name:
            is_running = component_module.status_check(self.app_state)

            if is_running is None:
                return

            if is_running is False:
                self.app_state.component_info.component_state = ComponentState.FAILED
                logger.error(f"{component_name} failed to start")

            elif is_running is True:
                self.app_state.component_info.component_state = ComponentState.RUNNING
                logger.debug(f"{component_name} online")
            self.app_state.component_store.update_status_file(self.app_state.component_info)
        else:
            raise Exception("neither component --id or component_name given")

    def node(self):
        """Essentially bitcoin-cli interface to RPC API that works 'out of the box' / zero config"""
        id = self.app_state.global_cli_flags[ComponentOptions.ID]
        if not id:
            id = "node1"
        component_dict = self.app_state.component_store.component_status_data_by_id(id)
        if component_dict:
            rpcport = component_dict.get("metadata").get("rpcport")
        else:
            logger.error(f"could not locate rpcport for node instance: {id}")

        self.app_state.node_args = cast_str_int_args_to_int(self.app_state.node_args)
        assert electrumsv_node.is_running(rpcport), (
            "bitcoin node must be running to respond to rpc methods. "
            "try: electrumsv-sdk start --node"
        )

        if self.app_state.node_args[0] in ["--help", "-h"]:
            self.app_state.node_args[0] = "help"

        result = electrumsv_node.call_any(
            self.app_state.node_args[0], *self.app_state.node_args[1:]
        )
        logger.info(result.json()["result"])

    def status(self):
        status = self.component_store.get_status()
        pprint.pprint(status, indent=4)
