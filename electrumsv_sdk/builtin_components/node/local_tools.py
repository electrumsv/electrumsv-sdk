import logging
import subprocess
import sys

import typing


if typing.TYPE_CHECKING:
    from .node import Plugin


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""


    def __init__(self, plugin: 'Plugin') -> None:
        self.plugin = plugin
        self.plugin_tools = self.plugin.plugin_tools
        self.config = plugin.config
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def process_cli_args(self) -> None:
        self.plugin_tools.set_network()

    def fetch_node(self) -> None:
        subprocess.run(f"{sys.executable} -m pip install electrumsv-node", shell=True, check=True)
