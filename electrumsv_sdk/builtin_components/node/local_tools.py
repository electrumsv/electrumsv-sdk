import logging
import subprocess
import sys

from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import Config

from .constants import NETWORKS_LIST


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin: AbstractPlugin):
        self.plugin = plugin
        self.plugin_tools = self.plugin.plugin_tools
        self.config: Config = plugin.config
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def set_network(self):
        # make sure that only one network is set on cli
        count_networks_selected = len([getattr(self.config, network) for network in NETWORKS_LIST if
            getattr(self.config, network) is True])
        if count_networks_selected > 1:
            self.logger.error("you must only select a single network")
            sys.exit(1)

        if count_networks_selected == 0:
            self.plugin.network = self.plugin.network
        if count_networks_selected == 1:
            for network in NETWORKS_LIST:
                if getattr(self.config, network):
                    self.plugin.network = network

    def process_cli_args(self):
        self.set_network()

    def fetch_node(self):
        subprocess.run(f"{sys.executable} -m pip install electrumsv-node", shell=True, check=True)
