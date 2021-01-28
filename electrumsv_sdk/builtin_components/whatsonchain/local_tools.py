import logging
import os
import subprocess

from electrumsv_node import electrumsv_node

from electrumsv_sdk.constants import REMOTE_REPOS_DIR
from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import Config
from electrumsv_sdk.utils import checkout_branch


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin: AbstractPlugin):
        self.plugin = plugin
        self.plugin_tools = self.plugin.plugin_tools
        self.config: Config = plugin.config
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

    def check_node_for_woc(self, rpchost: str="127.0.0.1", rpcport: int=18332,
            rpcuser: str="rpcuser", rpcpassword: str="rpcpassword"):
        if not electrumsv_node.is_running(rpcport, rpchost, rpcuser, rpcpassword):
            self.logger.error(f"bitcoin node {rpchost}:{rpcport} must be running")
            return False

        result = electrumsv_node.call_any("getinfo", rpcport=rpcport, rpchost=rpchost,
            rpcuser=rpcuser, rpcpassword=rpcpassword)
        block_height = result.json()['result']['blocks']
        if block_height == 0:
            self.logger.error(f"Block height=0. "
                 f"The Whatsonchain explorer requires at least 1 block to be mined. Hint: try: "
                 f"'electrumsv-sdk node generate 1'")
            return False
        return True
