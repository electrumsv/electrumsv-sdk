import logging
import sys
from typing import Optional

from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import ImmutableConfig
from electrumsv_sdk.plugin_tools import PluginTools
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import get_directory_name, kill_process

from .local_tools import LocalTools


class Plugin(AbstractPlugin):
    DEFAULT_PORT = 3002
    RESERVED_PORTS = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)
    logger = logging.getLogger(COMPONENT_NAME)

    def __init__(self, config: ImmutableConfig):
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
        self.tools.generate_run_script()
        if not self.tools.check_node_for_woc():
            sys.exit(1)

        script_path = self.plugin_tools.derive_shell_script_path(self.COMPONENT_NAME)
        process = self.plugin_tools.spawn_process(f"{script_path}")
        id = self.plugin_tools.get_id(self.COMPONENT_NAME)
        self.component_info = Component(id, process.pid, self.COMPONENT_NAME, str(self.src),
            "http://127.0.0.1:3002")

    def stop(self):
        """some components require graceful shutdown via a REST API or RPC API but most can use the
        generic 'app_state.kill_component()' function to track down the pid and kill the process."""
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance(s) (if any)")

    def reset(self):
        self.logger.info("resetting the whatsonchain is not applicable")

    def status_check(self) -> Optional[bool]:
        """
        True -> ComponentState.RUNNING;
        False -> ComponentState.FAILED;
        None -> skip status monitoring updates (e.g. using app's cli interface transiently)
        """
        is_running = self.plugin_tools.is_component_running_http(
            status_endpoint=self.component_info.status_endpoint,
            retries=4, duration=3, timeout=1.0, http_method='get')
        return is_running
