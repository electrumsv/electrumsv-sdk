import logging

from electrumsv_sdk.utils import get_directory_name
from electrumsv_sdk.config import Config


COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin):
        self.plugin = plugin
        self.config: Config = plugin.config
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def get_network_choice(self):
        network_options = [self.config.regtest, self.config.testnet, self.config.scaling_testnet,
            self.config.main]
        assert len([is_selected for is_selected in network_options if is_selected]) in {0, 1}, \
            "can only select 1 network"
        network_choice = "regtest"
        if self.config.testnet:
            network_choice = "testnet"
        elif self.config.scaling_testnet:
            network_choice = "scaling-testnet"
        elif self.config.main:
            network_choice = "main"
        return network_choice
