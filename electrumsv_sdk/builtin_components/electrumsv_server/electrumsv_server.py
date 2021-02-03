import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict
import shutil

from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import Config
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import get_directory_name, kill_process
from electrumsv_sdk.plugin_tools import PluginTools


MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class Plugin(AbstractPlugin):
    SERVER_HOST = "127.0.0.1"
    SERVER_PORT = 24242
    RESERVED_PORTS = {SERVER_PORT}

    COMPONENT_NAME = get_directory_name(__file__)
    COMPONENT_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
    ELECTRUMSV_SERVER_MODULE_PATH = Path(MODULE_DIR).parent.parent.parent.joinpath(
        "electrumsv-server")

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
        self.datadir, self.id = self.plugin_tools.get_component_datadir(self.COMPONENT_NAME)
        logfile = self.plugin_tools.get_logfile_path(self.id)
        env_vars = {"PYTHONUNBUFFERED": "1"}
        os.makedirs(self.ELECTRUMSV_SERVER_MODULE_PATH.joinpath("data"), exist_ok=True)
        os.chdir(self.ELECTRUMSV_SERVER_MODULE_PATH)
        command = f"{sys.executable} -m electrumsv_server --wwwroot-path=wwwroot " \
            f"--data-path={self.datadir}"

        self.plugin_tools.spawn_process(command, env_vars=env_vars, id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile, metadata={
            "datadir": str(self.datadir)}
        )

    def stop(self) -> None:
        self.logger.debug("Attempting to kill the process if it is even running")
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)

    def reset(self) -> None:
        def reset_server(component_dict: Dict):
            datadir = Path(component_dict.get("metadata").get("datadir"))
            if datadir.exists():
                shutil.rmtree(datadir)
                os.mkdir(datadir)
            else:
                os.makedirs(datadir, exist_ok=True)

        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=reset_server)
        self.logger.info(f"Reset of {self.COMPONENT_NAME} completed successfully.")
