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
        self.config = plugin.cli_inputs
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def process_cli_args(self) -> None:
        self.plugin_tools.set_network()

    def fetch_node(self) -> None:
        assert self.plugin.config.PYTHON_LIB_DIR is not None  # typing bug
        assert self.plugin.COMPONENT_NAME is not None  # typing bug
        node_libs_path = self.plugin.config.PYTHON_LIB_DIR / self.plugin.COMPONENT_NAME
        subprocess.run(f"{sys.executable} -m pip install --target {node_libs_path} --upgrade "
            f"electrumsv-node", shell=True, check=True)
