import logging
import os
import subprocess
import sys

from electrumsv_node import electrumsv_node

from electrumsv_sdk.constants import SHELL_SCRIPTS_DIR, REMOTE_REPOS_DIR
from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import ImmutableConfig
from electrumsv_sdk.utils import checkout_branch


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin: AbstractPlugin):
        self.plugin = plugin
        self.plugin_tools = self.plugin.plugin_tools
        self.config: ImmutableConfig = plugin.config
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def fetch_whatsonchain(self, url="https://github.com/AustEcon/woc-explorer.git",
                           branch=''):
        if not self.plugin.src.exists():
            os.makedirs(self.plugin.src, exist_ok=True)
            os.chdir(REMOTE_REPOS_DIR)
            subprocess.run(f"git clone {url}", shell=True, check=True)

            os.chdir(self.plugin.src)
            checkout_branch(branch)

    def packages_whatsonchain(self):
        os.chdir(self.plugin.src)
        process = subprocess.Popen("npm install", shell=True)
        process.wait()
        process = subprocess.Popen("npm run-script build", shell=True)
        process.wait()

    def generate_run_script(self):
        if not self.plugin.src.exists():
            self.logger.error(f"source code directory does not exist - try 'electrumsv-sdk install "
                              f"{self.plugin.COMPONENT_NAME}' to install the plugin first")
            sys.exit(1)

        os.makedirs(SHELL_SCRIPTS_DIR, exist_ok=True)
        os.chdir(SHELL_SCRIPTS_DIR)
        line1 = f"cd {self.plugin.src}"
        line2 = f"call npm start" if sys.platform == "win32" else f"npm start"
        self.plugin_tools.make_shell_script_for_component(list_of_shell_commands=[line1, line2],
            component_name=self.plugin.COMPONENT_NAME)

    def check_node_for_woc(self):
        if not electrumsv_node.is_running():
            self.logger.error("bitcoin node must be running")
            return False

        result = electrumsv_node.call_any("getinfo")
        block_height = result.json()['result']['blocks']
        if block_height == 0:
            self.logger.error(f"Block height=0. "
                 f"The Whatsonchain explorer requires at least 1 block to be mined. Hint: try: "
                 f"'electrumsv-sdk node generate 1'")
            return False
        return True
