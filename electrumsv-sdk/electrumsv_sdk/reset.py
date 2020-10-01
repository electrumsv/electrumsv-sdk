import logging
import os
import shutil
import time

from electrumsv_node import electrumsv_node

from .install_tools import InstallTools
from .stoppers import Stoppers
from .components import ComponentName, ComponentOptions
from .installers import Installers
from .starters import Starters
from .utils import topup_wallet, create_wallet, delete_wallet

logger = logging.getLogger("main")
orm_logger = logging.getLogger("peewee")
orm_logger.setLevel(logging.WARNING)


class Resetters:
    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.starters = Starters(self.app_state)
        self.stoppers = Stoppers(self.app_state)
        self.installers = Installers(self.app_state)
        self.install_tools = InstallTools(self.app_state)

    def reset_node(self):
        electrumsv_node.reset()
        logger.debug("Reset of RegTest bitcoin daemon completed successfully.")

    def reset_electrumx(self):
        logger.debug("Resetting state of RegTest electrumx server...")
        # Todo - set repo and branch
        electrumx_data_dir = self.app_state.electrumx_data_dir
        if electrumx_data_dir.exists():
            shutil.rmtree(electrumx_data_dir)
            os.mkdir(electrumx_data_dir)
        else:
            os.makedirs(electrumx_data_dir, exist_ok=True)
        logger.debug("Reset of RegTest electrumx server completed successfully.")

    def launch_esv_dependencies(self, component_id):
        """ElectrumSV requires ElectrumX and Node to be running."""
        self.app_state.start_set.add(ComponentName.NODE)
        self.app_state.start_set.add(ComponentName.ELECTRUMX)
        self.app_state.start_set.add(ComponentName.ELECTRUMSV)

        repo = self.app_state.start_options[ComponentOptions.REPO]
        branch = self.app_state.start_options[ComponentOptions.BRANCH]

        self.install_tools.setup_paths_and_shell_scripts_electrumsv()
        self.app_state.installers.local_electrumsv(repo, branch)

        new_dir = self.installers.get_electrumsv_data_dir(id=component_id)
        port = self.installers.get_electrumsv_port()
        self.app_state.update_electrumsv_data_dir(new_dir, port)

        self.starters.start()
        logger.debug("Allowing time for the electrumsv daemon to boot up - standby...")
        time.sleep(7)

    def reset_electrumsv_wallet(self, component_id=None):
        """depends on having node and electrumx already running"""
        self.launch_esv_dependencies(component_id)
        logger.debug("Resetting state of RegTest electrumsv server...")
        if component_id is None:
            logger.warning("Note: No --id flag is specified. Therefore the default 'electrumsv1' "
                "instance will be reset.")
        delete_wallet(self.app_state)
        create_wallet()
        topup_wallet()
        logger.debug("Reset of RegTest electrumsv wallet completed successfully")
