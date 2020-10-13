import pprint

import logging
import sys
import time

from electrumsv_node import electrumsv_node
from electrumsv_sdk.components import ComponentName, ComponentStore, ComponentOptions, ComponentType

from .reset import Resetters
from .installers import Installers
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
        self.installers = Installers(self.app_state)
        self.component_store = ComponentStore(self.app_state)

    def start(self):
        logger.info("Starting component...")
        open(self.app_state.electrumsv_sdk_data_dir / "spawned_pids", 'w').close()

        procs = []

        if not self.starters.is_status_monitor_running():
            status_monitor_process = self.starters.start_status_monitor()
            procs.append(status_monitor_process.pid)

        if ComponentName.NODE in self.app_state.start_set \
                or len(self.app_state.start_set) == 0:
            self.starters.start_node()
            time.sleep(2)

        if ComponentName.ELECTRUMX in self.app_state.start_set \
                or len(self.app_state.start_set) == 0:
            electrumx_process = self.starters.start_electrumx()
            procs.append(electrumx_process.pid)

        if ComponentName.ELECTRUMSV in self.app_state.start_set \
                or len(self.app_state.start_set) == 0:
            if sys.version_info[:3] < (3, 7, 8):
                sys.exit("Error: ElectrumSV requires Python version >= 3.7.8...")

            esv_process = self.starters.start_electrumsv()
            if esv_process:
                procs.append(esv_process.pid)

        if ComponentName.WHATSONCHAIN in self.app_state.start_set \
                or len(self.app_state.start_set) == 0:
            woc_process = self.starters.start_whatsonchain()
            procs.append(woc_process.pid)

        self.app_state.save_repo_paths()

    def stop(self):
        """if stop_set is empty, all processes terminate."""
        # todo: make this granular enough to pick out instances of each component type

        if ComponentName.NODE in self.app_state.stop_set or len(self.app_state.stop_set) == 0:
            self.stoppers.stop_components_by_type(ComponentType.NODE)

        if ComponentName.ELECTRUMSV in self.app_state.stop_set or len(self.app_state.stop_set) == 0:
            self.stoppers.stop_components_by_type(ComponentType.ELECTRUMSV)

        if ComponentName.ELECTRUMX in self.app_state.stop_set or len(self.app_state.stop_set) == 0:
            self.stoppers.stop_components_by_type(ComponentType.ELECTRUMX)

        if ComponentName.INDEXER in self.app_state.stop_set or len(self.app_state.stop_set) == 0:
            self.stoppers.stop_components_by_type(ComponentType.INDEXER)

        if ComponentName.STATUS_MONITOR in self.app_state.stop_set \
                or len(self.app_state.stop_set) == 0:
            self.stoppers.stop_components_by_type(ComponentType.STATUS_MONITOR)

        if ComponentName.WHATSONCHAIN in self.app_state.stop_set \
                or len(self.app_state.stop_set) == 0:
            self.stoppers.stop_components_by_type(ComponentType.WOC)

        logger.info(f"terminated: "
                    f"{self.app_state.stop_set if len(self.app_state.stop_set) != 0 else 'all'}")

    def reset(self):
        """No choice is given to the user at present - resets node, electrumx and electrumsv
        wallet. If stop_set is empty, all processes terminate."""
        self.app_state.start_options[ComponentOptions.BACKGROUND] = True

        component_id = self.app_state.start_options[ComponentOptions.ID]
        if self.app_state.start_options[ComponentOptions.ID] != "":
            if len(self.app_state.reset_set) != 0:
                logger.debug(f"The '--id' flag is specified, therefore ignoring the component "
                             f"type(s): {self.app_state.reset_set}")
            self.resetters.reset_component_by_id(component_id)
        else:
            self.resetters.reset_component_by_type()

        if self.app_state.start_options[ComponentOptions.ID] == "":
            logger.info(f"Reset of: "
                f"{self.app_state.reset_set if len(self.app_state.reset_set) != 0 else 'all'} "
                        f"complete.")
        else:
            logger.info(f"Reset of: {self.app_state.start_options[ComponentOptions.ID]} complete.")

        self.app_state.stop_set.add(ComponentName.STATUS_MONITOR)
        self.stop()

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
