import logging

import typing

from electrumsv_sdk.utils import get_directory_name


COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)

if typing.TYPE_CHECKING:
    from .electrumsv_server import Plugin


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin: 'Plugin'):
        self.plugin = plugin
        self.config = plugin.config
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def get_network_choice(self) -> str:
        network_options = [
            self.config.cli_extension_args['regtest'],
            self.config.cli_extension_args['testnet'],
            self.config.cli_extension_args['scaling_testnet'],
            self.config.cli_extension_args['main']
        ]
        assert len([is_selected for is_selected in network_options if is_selected]) in {0, 1}, \
            "can only select 1 network"
        network_choice = "regtest"
        if self.config.cli_extension_args['testnet']:
            network_choice = "testnet"
        elif self.config.cli_extension_args['scaling_testnet']:
            network_choice = "scaling-testnet"
        elif self.config.cli_extension_args['main']:
            network_choice = "main"
        return network_choice
