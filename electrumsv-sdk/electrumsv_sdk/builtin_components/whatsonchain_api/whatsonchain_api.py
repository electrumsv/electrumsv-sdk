import logging
import os
import sys
from pathlib import Path
from typing import Optional

from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import Config
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

    def __init__(self, config: Config):
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
        self.id = self.plugin_tools.get_id(self.COMPONENT_NAME)
        command = f"{sys.executable} {self.SCRIPT_PATH}"
        logfile = self.plugin_tools.get_logfile_path(self.id)
        env_vars = {"PYTHONUNBUFFERED": "1"}
        self.plugin_tools.spawn_process(command, env_vars=env_vars, id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            status_endpoint=self.PING_URL
        )

    def stop(self) -> None:
        self.logger.debug("Attempting to kill the process if it is even running")
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)

    def reset(self) -> None:
        pass
