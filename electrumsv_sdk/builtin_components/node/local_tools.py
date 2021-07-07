import logging
import subprocess
import sys

import typing

from electrumsv_sdk.types import AbstractLocalTools
from electrumsv_sdk.config import Config


if typing.TYPE_CHECKING:
    from electrumsv_sdk.builtin_components.node import Plugin


class LocalTools(AbstractLocalTools):
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""


    def __init__(self, plugin: 'Plugin'):
        self.plugin = plugin
        self.plugin_tools = self.plugin.plugin_tools
        self.config: Config = plugin.config
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def process_cli_args(self):
        self.plugin_tools.set_network()

    def fetch_node(self):
        subprocess.run(f"{sys.executable} -m pip install electrumsv-node", shell=True, check=True)
