import pprint

import logging
import time
from electrumsv_node import electrumsv_node
from electrumsv_sdk.components import ComponentName, ComponentStore, ComponentOptions

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

    def reset(self):
        """no choice is given to the user at present - resets node, electrumx and electrumsv
        wallet"""

        # Todo - these should be set via the cli similar to the start command
        self.app_state.start_options[ComponentOptions.BACKGROUND] = True
        self.app_state.start_options[ComponentOptions.NEW] = False
        self.app_state.start_options[ComponentOptions.ID] = ""
        
        self.app_state.load_repo_paths()
        self.app_state.resetters.reset_node()
        self.app_state.resetters.reset_electrumx()

        self.app_state.start_set.add(ComponentName.NODE)
        self.app_state.start_set.add(ComponentName.ELECTRUMX)
        self.app_state.start_set.add(ComponentName.ELECTRUMSV)

        self.app_state.set_electrumsv_path(self.app_state.depends_dir.joinpath("electrumsv"))
        new_dir = self.installers.get_electrumsv_data_dir()
        port = self.installers.get_electrumsv_port()
        self.app_state.update_electrumsv_data_dir(new_dir, port)

        self.start()
        logger.debug("Allowing time for the electrumsv daemon to boot up - standby...")
        time.sleep(7)
        self.app_state.resetters.reset_electrumsv_wallet()
        self.stop()

