import logging
import os
import sys
from pathlib import Path
from typing import Optional

from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import ImmutableConfig
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import get_directory_name, kill_process
from electrumsv_sdk.plugin_tools import PluginTools

from . import server_app


class Plugin(AbstractPlugin):
    SERVER_HOST = server_app.SERVER_HOST
    SERVER_PORT = server_app.SERVER_PORT
    RESERVED_PORTS = {SERVER_PORT}
    PING_URL = server_app.PING_URL

    COMPONENT_NAME = get_directory_name(__file__)
    COMPONENT_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
    SCRIPT_PATH = COMPONENT_PATH / "server_app.py"

    def __init__(self, config: ImmutableConfig):
        self.config = config
        self.plugin_tools = PluginTools(self, self.config)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.COMPONENT_PATH
        self.datadir = None  # dynamically allocated
        self.id = None  # dynamically allocated
        self.port = None  # dynamically allocated
        self.component_info: Optional[Component] = None

    def install(self) -> None:
        self.logger.debug(f"Installing {self.COMPONENT_NAME} is not applicable")

    def start(self) -> None:
        id = self.plugin_tools.get_id(self.COMPONENT_NAME)
        process = self.plugin_tools.spawn_process(f"{sys.executable} {self.SCRIPT_PATH}")
        self.component_info = Component(id, process.pid, self.COMPONENT_NAME,
            self.COMPONENT_PATH, self.PING_URL)

    def stop(self) -> None:
        self.logger.debug("Attempting to kill the process if it is even running")
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)

    def reset(self) -> None:
        pass

    def status_check(self) -> Optional[bool]:
        """
        True -> ComponentState.RUNNING;
        False -> ComponentState.FAILED;
        None -> skip status monitoring updates (e.g. using app's cli interface transiently)
        """
        is_running = self.plugin_tools.is_component_running_http(
            status_endpoint=self.component_info.status_endpoint,
            retries=5, duration=2, timeout=1.0)
        return is_running
