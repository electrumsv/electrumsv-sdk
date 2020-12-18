import logging
import subprocess
import sys

from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import Config


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin: AbstractPlugin):
        self.plugin = plugin
        self.plugin_tools = self.plugin.plugin_tools
        self.config: Config = plugin.config
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def fetch_node(self):
        subprocess.run(f"{sys.executable} -m pip install electrumsv-node", shell=True, check=True)
