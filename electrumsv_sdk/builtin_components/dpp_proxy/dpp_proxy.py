import logging
import os
import sys
from pathlib import Path
from typing import Optional, Set

from electrumsv_sdk.sdk_types import AbstractPlugin
from electrumsv_sdk.config import CLIInputs, Config
from electrumsv_sdk.components import Component, ComponentTypedDict
from electrumsv_sdk.utils import get_directory_name, kill_process
from electrumsv_sdk.plugin_tools import PluginTools

from .install import download_and_install, get_run_command, load_env_vars, DPP_PROXY_VERSION, \
    chmod_exe


class Plugin(AbstractPlugin):

    DEFAULT_PORT = 8445
    RESERVED_PORTS: Set[int] = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)

    def __init__(self, cli_inputs: CLIInputs):
        self.cli_inputs = cli_inputs
        self.config = Config()
        self.plugin_tools = PluginTools(self, self.cli_inputs)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.plugin_tools.get_source_dir(dirname="dpp_proxy")
        self.datadir: Optional[Path] = None  # dynamically allocated
        self.id: Optional[str] = None  # dynamically allocated
        self.port: Optional[int] = None  # dynamically allocated
        self.component_info: Optional[Component] = None

    def install(self) -> None:
        assert self.src is not None  # typing bug in mypy
        download_and_install(self.src)

        self.logger.debug(f"Installed {self.COMPONENT_NAME}")

    def start(self) -> None:
        assert self.src is not None  # typing bug

        self.logger.debug(f"Starting {self.COMPONENT_NAME}")
        if not self.src.exists():
            self.logger.error(f"source code directory does not exist - try 'electrumsv-sdk install "
                              f"{self.COMPONENT_NAME}' to install the plugin first")
            sys.exit(1)

        self.id = self.plugin_tools.get_id(self.COMPONENT_NAME)
        self.port = self.DEFAULT_PORT
        # The primary reason we need this to be the current directory is so that the `settings.conf`
        # file is directly accessible to the MAPI executable (it should look there first).
        os.chdir(self.src)

        # EXE RUN MODE
        load_env_vars()
        try:
            command = get_run_command(self.src)
            chmod_exe(self.src)
        except FileNotFoundError:
            self.logger.error(f"Could not find version: {DPP_PROXY_VERSION} of "
                f"{self.COMPONENT_NAME}. Have you tried re-running 'electrumsv-sdk install "
                f"{self.COMPONENT_NAME}' to pull the latest version?")
            return

        logfile = self.plugin_tools.get_logfile_path(self.id)
        status_endpoint = f"http://localhost:{self.DEFAULT_PORT}"

        self.plugin_tools.spawn_process(str(command), env_vars=os.environ.copy(), id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            status_endpoint=status_endpoint)

    def stop(self) -> None:
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance (if running)")

    def reset(self) -> None:

        def reset_dpp_proxy(component_dict: ComponentTypedDict) -> None:
            pass

        self.plugin_tools.call_for_component_id_or_type(
            self.COMPONENT_NAME, callable=reset_dpp_proxy)
        self.logger.info(f"Reset of {self.COMPONENT_NAME} completed successfully "
                         f"(there is no database)")
