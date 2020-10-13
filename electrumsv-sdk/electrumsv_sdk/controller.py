import pprint

import logging
import sys

from electrumsv_node import electrumsv_node
from electrumsv_sdk.components import ComponentName, ComponentStore, ComponentOptions, ComponentType

from .constants import DEFAULT_ID_NODE, DEFAULT_ID_ELECTRUMX
from .reset import Resetters
from .installers import Installers
from .handlers import Handlers
from .starters import Starters
from .stoppers import Stoppers
from .utils import cast_str_int_args_to_int

logger = logging.getLogger("runners")


class Controller:
    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.starters = Starters(self.app_state)
        self.stoppers = Stoppers(self.app_state)
        self.resetters = Resetters(self.app_state)
        self.handlers = Handlers(self.app_state)
        self.installers = Installers(self.app_state)
        self.component_store = ComponentStore(self.app_state)

    def start(self):
        self.starters.start()

    def stop(self):
        self.stoppers.stop()

    def node(self):
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

    def reset_component_by_id(self, component_id):
        if self.app_state.start_options[ComponentOptions.ID] != "":
            if len(self.app_state.reset_set) != 0:
                logger.debug(f"The '--id' flag is specified "
                             f"- ignoring the component type(s) {self.app_state.reset_set}")

        component_data = self.component_store.component_data_by_id(component_id)
        if component_data == {}:
            sys.exit(1)

        if component_data.get('process_type') == ComponentType.NODE:
            logger.debug(f"There is only one 'id' for this component type - resetting the "
                         f"default node id={DEFAULT_ID_NODE}")
            self.resetters.reset_node()

        elif component_data.get('process_type') == ComponentType.ELECTRUMX:
            logger.debug(f"There is only one 'id' for this component type - resetting the "
                         f"default electrumx id={DEFAULT_ID_ELECTRUMX}")
            self.resetters.reset_electrumx()

        elif component_data.get('process_type') == ComponentType.ELECTRUMSV:
            self.resetters.reset_electrumsv_wallet(component_id)

        elif component_data.get('process_type') == ComponentType.INDEXER:
            logger.debug(f"The Indexer component type is not supported at this time.")

        elif component_data.get('process_type') == ComponentType.STATUS_MONITOR:
            logger.error("resetting the status monitor is not supported at this time...")

    def reset_component_by_type(self):
        if ComponentName.NODE in self.app_state.reset_set or len(self.app_state.reset_set) == 0:
            self.resetters.reset_node()

        if ComponentName.ELECTRUMX in self.app_state.reset_set or len(
                self.app_state.reset_set) == 0:
            self.resetters.reset_electrumx()

        if ComponentName.INDEXER in self.app_state.reset_set or len(
                self.app_state.reset_set) == 0:
            logger.error("resetting indexer is not supported at this time...")

        if ComponentName.STATUS_MONITOR in self.app_state.reset_set \
                or len(self.app_state.reset_set) == 0:
            logger.error("resetting the status monitor is not supported at this time...")

        if ComponentName.ELECTRUMSV in self.app_state.reset_set or len(
                self.app_state.reset_set) == 0:
            self.resetters.reset_electrumsv_wallet()
            self.app_state.stop_set.add(ComponentName.ELECTRUMSV)

    def reset(self):
        """No choice is given to the user at present - resets node, electrumx and electrumsv
        wallet. If stop_set is empty, all processes terminate."""
        self.app_state.start_options[ComponentOptions.BACKGROUND] = True

        component_id = self.app_state.start_options[ComponentOptions.ID]
        if self.app_state.start_options[ComponentOptions.ID] != "":
            if len(self.app_state.reset_set) != 0:
                logger.debug(f"The '--id' flag is specified, therefore ignoring the component "
                             f"type(s): {self.app_state.reset_set}")
            self.reset_component_by_id(component_id)
        else:
            self.reset_component_by_type()

        if self.app_state.start_options[ComponentOptions.ID] == "":
            logger.info(f"Reset of: "
                f"{self.app_state.reset_set if len(self.app_state.reset_set) != 0 else 'all'} "
                        f"complete.")
        else:
            logger.info(f"Reset of: {self.app_state.start_options[ComponentOptions.ID]} complete.")

        self.app_state.stop_set.add(ComponentName.STATUS_MONITOR)
        self.stoppers.stop()
