import logging
import os
import sys
from typing import Optional

from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import Config
from electrumsv_sdk.plugin_tools import PluginTools
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import get_directory_name, kill_process

from .local_tools import LocalTools


class Plugin(AbstractPlugin):

    # As per woc-explorer/config.js
    ELECTRUMX_HOST = os.environ.get("ELECTRUMX_HOST") or "127.0.0.1"
    ELECTRUMX_PORT = os.environ.get("ELECTRUMX_PORT") or 51001

    # As per woc-explorer/app.js
    RPC_HOST = os.environ.get("RPC_HOST") or "127.0.0.1"
    RPC_PORT = os.environ.get("RPC_PORT") or 18332
    RPC_USERNAME = os.environ.get("RPC_USERNAME") or "rpcuser"
    RPC_PASSWORD = os.environ.get("RPC_PASSWORD") or "rpcpassword"

    DEFAULT_PORT = 3002
    RESERVED_PORTS = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)
    logger = logging.getLogger(COMPONENT_NAME)

    def __init__(self, config: Config):
        self.config = config
        self.plugin_tools = PluginTools(self, self.config)
        self.tools = LocalTools(self)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.plugin_tools.get_source_dir("woc-explorer")
        self.datadir = None  # N/A
        self.id = self.plugin_tools.get_id(self.COMPONENT_NAME)
        self.port = None  # N/A
        self.component_info: Optional[Component] = None

    def install(self):
        if not self.config.repo == "":  # default
            self.logger.error("ignoring --repo flag for whatsonchain - not applicable.")
        self.tools.fetch_whatsonchain(url="https://github.com/AustEcon/woc-explorer.git", branch='')
        self.tools.packages_whatsonchain()
        self.logger.debug(f"Installed {self.COMPONENT_NAME}")

    def start(self):
        self.logger.debug(f"Starting whatsonchain explorer...")

        if not self.src.exists():
            self.logger.error(f"source code directory does not exist - try 'electrumsv-sdk install "
                              f"{self.COMPONENT_NAME}' to install the plugin first")
            sys.exit(1)

        if not self.tools.check_node_for_woc(self.RPC_HOST, self.RPC_PORT, self.RPC_USERNAME,
                self.RPC_PASSWORD):
            sys.exit(1)

        os.chdir(self.src)
        # npm without .cmd extension doesn't work with Popen shell=False
        if sys.platform == "win32":
            command = f"npm.cmd start"
        elif sys.platform in {"linux", "darwin"}:
            command = f"npm start"
        env_vars = {
            "PYTHONUNBUFFERED": "1",
            "ELECTRUMX_HOST": self.ELECTRUMX_HOST,
            "ELECTRUMX_PORT": str(self.ELECTRUMX_PORT),
            "RPC_HOST": self.RPC_HOST,
            "RPC_PORT": str(self.RPC_PORT),
            "RPC_USERNAME": self.RPC_USERNAME,
            "RPC_PASSWORD": self.RPC_PASSWORD,
        }
        self.id = self.plugin_tools.get_id(self.COMPONENT_NAME)
        logfile = self.plugin_tools.get_logfile_path(self.id)
        status_endpoint="http://127.0.0.1:3002"
        self.plugin_tools.spawn_process(command, env_vars=env_vars, id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            status_endpoint=status_endpoint
        )

    def stop(self):
        """some components require graceful shutdown via a REST API or RPC API but most can use the
        generic 'app_state.kill_component()' function to track down the pid and kill the process."""
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance(s) (if any)")

    def reset(self):
        self.logger.info("resetting the whatsonchain is not applicable")
