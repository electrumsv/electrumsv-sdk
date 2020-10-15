import pprint

import logging
import sys
import time
import importlib

from electrumsv_node import electrumsv_node

from electrumsv_sdk.components import ComponentStore, ComponentOptions, ComponentName

from .constants import STATUS_MONITOR_GET_STATUS
from .reset import Resetters
from .handlers import Handlers
from .starters import Starters
from .stoppers import Stoppers
from .utils import cast_str_int_args_to_int

logger = logging.getLogger("runners")


class Controller:
    """Five main execution pathways (corresponding to 5 cli commands)"""

    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.starters = Starters(self.app_state)
        self.stoppers = Stoppers(self.app_state)
        self.resetters = Resetters(self.app_state)
        self.handlers = Handlers(self.app_state)
        self.component_store = ComponentStore(self.app_state)

    def install(self, component_name: str=None):
        component_name = component_name if component_name \
            else self.app_state.selected_start_component
        component = importlib.import_module(f'.{component_name}',
                                            package='electrumsv_sdk.builtin_components')
        component.install(self.app_state)

    def start(self):
        logger.info("Starting component...")
        open(self.app_state.electrumsv_sdk_data_dir / "spawned_pids", 'w').close()

        if not self.starters.is_component_running(ComponentName.STATUS_MONITOR,
                STATUS_MONITOR_GET_STATUS, 3, 0.5):
            self.install(ComponentName.STATUS_MONITOR)
            self.starters.start_status_monitor()

        if ComponentName.NODE == self.app_state.selected_start_component:
            self.starters.start_node()
            time.sleep(2)

        if ComponentName.ELECTRUMX == self.app_state.selected_start_component:
            self.starters.start_electrumx()

        if ComponentName.ELECTRUMSV == self.app_state.selected_start_component:
            if sys.version_info[:3] < (3, 7, 8):
                sys.exit("Error: ElectrumSV requires Python version >= 3.7.8...")
            self.starters.start_electrumsv()

        if ComponentName.WHATSONCHAIN == self.app_state.selected_start_component:
            self.starters.start_whatsonchain()

        self.app_state.save_repo_paths()

        # no args implies (node, electrumx, electrumsv, whatsonchain)
        # call sdk recursively to achieve this (greatly simplifies code)
        if not self.app_state.selected_start_component:
            self.starters.run_command_current_shell("electrumsv-sdk start node")
            self.starters.run_command_current_shell("electrumsv-sdk start electrumx")
            self.starters.run_command_current_shell("electrumsv-sdk start electrumsv")
            self.starters.run_command_current_shell("electrumsv-sdk start whatsonchain")

    def stop(self):
        """if stop_set is empty, all processes terminate."""
        # todo: make this granular enough to pick out instances of each component type
        self.app_state.start_options[ComponentOptions.BACKGROUND] = True

        if ComponentName.NODE == self.app_state.selected_stop_component:
            self.stoppers.stop_components_by_name(ComponentName.NODE)

        if ComponentName.ELECTRUMSV == self.app_state.selected_stop_component:
            self.stoppers.stop_components_by_name(ComponentName.ELECTRUMSV)

        if ComponentName.ELECTRUMX == self.app_state.selected_stop_component:
            self.stoppers.stop_components_by_name(ComponentName.ELECTRUMX)

        if ComponentName.INDEXER == self.app_state.selected_stop_component:
            self.stoppers.stop_components_by_name(ComponentName.INDEXER)

        if ComponentName.STATUS_MONITOR == self.app_state.selected_stop_component:
            self.stoppers.stop_components_by_name(ComponentName.STATUS_MONITOR)

        if ComponentName.WHATSONCHAIN == self.app_state.selected_stop_component:
            self.stoppers.stop_components_by_name(ComponentName.WHATSONCHAIN)

        if self.app_state.selected_stop_component:
            logger.info(f"terminated: {self.app_state.selected_stop_component}")

        # no args implies stop all (status_monitor, node, electrumx, electrumsv, whatsonchain)
        # call sdk recursively to achieve this (greatly simplifies code)
        if not self.app_state.selected_stop_component:
            self.starters.run_command_current_shell("electrumsv-sdk stop node")
            self.starters.run_command_current_shell("electrumsv-sdk stop electrumx")
            self.starters.run_command_current_shell("electrumsv-sdk stop electrumsv")
            self.starters.run_command_current_shell("electrumsv-sdk stop whatsonchain")
            self.starters.run_command_current_shell("electrumsv-sdk stop status_monitor")
            logger.info(f"terminated: all")


    def reset(self):
        """No choice is given to the user at present - resets node, electrumx and electrumsv
        wallet. If stop_set is empty, all processes terminate."""
        self.app_state.start_options[ComponentOptions.BACKGROUND] = True

        component_id = self.app_state.start_options[ComponentOptions.ID]
        if self.app_state.start_options[ComponentOptions.ID] != "":
            component_data = self.component_store.component_status_data_by_id(component_id)
            component_name = component_data.get('component_type')
            if component_data == {}:
                logger.error("no component data found - cannot complete reset")
                sys.exit(1)
            self.resetters.reset_component(component_name, component_id)

        elif self.app_state.start_options[ComponentOptions.ID] == "" and \
                self.app_state.selected_reset_component:
            component_name = self.app_state.selected_reset_component
            self.resetters.reset_component(component_name)

        # no args (no --id or component_type) implies reset all (node, electrumx, electrumsv)
        # call sdk recursively to achieve this (greatly simplifies code)
        elif self.app_state.start_options[ComponentOptions.ID] == "" and not \
                self.app_state.selected_reset_component:
            self.starters.run_command_current_shell("electrumsv-sdk reset node")
            self.starters.run_command_current_shell("electrumsv-sdk reset electrumx")
            self.starters.run_command_current_shell("electrumsv-sdk reset electrumsv")

        if self.app_state.start_options[ComponentOptions.ID] == "" and \
                self.app_state.selected_reset_component:
            logger.info(f"Reset of: {self.app_state.selected_reset_component} complete.")
        elif self.app_state.start_options[ComponentOptions.ID] != "":
            logger.info(f"Reset of: {self.app_state.start_options[ComponentOptions.ID]} complete.")
        elif not self.app_state.selected_reset_component:
            logger.info(f"Reset of: all components complete")

        self.starters.run_command_current_shell("electrumsv-sdk stop status_monitor")

    def node(self):
        """Essentially bitcoin-cli interface to RPC API that works 'out of the box' / zero config"""
        self.app_state.node_args = cast_str_int_args_to_int(self.app_state.node_args)
        assert electrumsv_node.is_running(), (
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
