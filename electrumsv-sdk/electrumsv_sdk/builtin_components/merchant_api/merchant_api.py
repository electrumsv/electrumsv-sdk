import logging
import os
import sys
from typing import Optional

from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import ImmutableConfig
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import get_directory_name, kill_process
from electrumsv_sdk.plugin_tools import PluginTools

from .install import download_and_install, create_settings_file, get_run_path


class Plugin(AbstractPlugin):

    NODE_RPC_PORT = 18332
    NODE_RPC_USERNAME = "rpcuser"
    NODE_RPC_PASSWORD = "rpcpassword"
    NODE_ZMQ_PORT = 28332

    DEFAULT_PORT = 45111
    RESERVED_PORTS = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)

    def __init__(self, config: ImmutableConfig):
        self.config = config
        self.plugin_tools = PluginTools(self, self.config)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.plugin_tools.get_source_dir(dirname="merchant_api")
        self.datadir = None  # dynamically allocated
        self.id = None  # dynamically allocated
        self.port = None  # dynamically allocated
        self.component_info: Optional[Component] = None

    def install(self):
        download_and_install(self.src)
        create_settings_file(self.src, self.DEFAULT_PORT, self.NODE_RPC_PORT,
            self.NODE_RPC_USERNAME, self.NODE_RPC_PASSWORD, self.NODE_ZMQ_PORT)
        self.logger.debug(f"Installed {self.COMPONENT_NAME}")

    def start(self):
        self.logger.debug(f"Starting Merchant API")
        if not self.src.exists():
            self.logger.error(f"source code directory does not exist - try 'electrumsv-sdk install "
                              f"{self.COMPONENT_NAME}' to install the plugin first")
            sys.exit(1)

        self.id = self.plugin_tools.get_id(self.COMPONENT_NAME)
        self.port = self.plugin_tools.allocate_port()
        # The primary reason we need this to be the current directory is so that the `settings.conf`
        # file is directly accessible to the MAPI executable (it should look there first).
        os.chdir(self.src)
        # Get the path to the executable file.
        run_path = get_run_path(self.src)
        process = self.plugin_tools.spawn_process(str(run_path))
        self.component_info = Component(self.id, process.pid, self.COMPONENT_NAME,
            self.src, "???")

    def stop(self):
        """some components require graceful shutdown via a REST API or RPC API but most can use the
        generic 'app_state.kill_component()' function to track down the pid and kill the process."""
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance(s) (if any)")

    def reset(self):
        self.logger.info("resetting Merchant API is not applicable")

    def status_check(self) -> Optional[bool]:
        """
        True -> ComponentState.RUNNING;
        False -> ComponentState.FAILED;
        None -> skip status monitoring updates (e.g. using app's cli interface transiently)
        """
        # is_running = app_state.is_component_running_http(
        #     status_endpoint=app_state.component_info.status_endpoint,
        #     retries=4, duration=3, timeout=1.0, http_method='get')
        return True
