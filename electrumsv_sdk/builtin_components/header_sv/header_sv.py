import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Set

from electrumsv_sdk.sdk_types import AbstractPlugin
from electrumsv_sdk.config import CLIInputs, Config
from electrumsv_sdk.components import Component, ComponentTypedDict
from electrumsv_sdk.utils import get_directory_name, kill_process
from electrumsv_sdk.plugin_tools import PluginTools

from .install import download_and_install, get_run_command, HEADER_SV_VERSION, \
    load_env_vars



class Plugin(AbstractPlugin):

    DEFAULT_PORT = 33444
    RESERVED_PORTS: Set[int] = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)

    HEADERSV_NETWORK_GENESISHEADERHEX = "01000000000000000000000000000000000000000000000000000000" \
        "00000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4adae5494d" \
        "ffff7f2002000000"

    def __init__(self, cli_inputs: CLIInputs):
        self.cli_inputs = cli_inputs
        self.config = Config()
        self.plugin_tools = PluginTools(self, self.cli_inputs)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.plugin_tools.get_source_dir(dirname="header_sv")
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

        self.logger.debug(f"Starting Header SV")
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
        except FileNotFoundError:
            self.logger.error(f"Could not find version: {HEADER_SV_VERSION} of "
                f"HeaderSV. Have you tried re-running 'electrumsv-sdk install "
                f"{self.COMPONENT_NAME}' to pull the latest version?")
            return

        logfile = self.plugin_tools.get_logfile_path(self.id)
        status_endpoint = "http://localhost:33444/api/v1/chain/tips"

        # NOTE(rt12) HeaderSV 2.0.2 appears to have the wrong genesis block for regtest.
        # https://github.com/bitcoin-sv/block-headers-client/pull/20
        environment = os.environ.copy()
        environment.setdefault("HEADERSV_NETWORK_GENESISHEADERHEX",
            self.HEADERSV_NETWORK_GENESISHEADERHEX)

        self.plugin_tools.spawn_process(str(command), env_vars=environment, id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            status_endpoint=status_endpoint)

    def stop(self) -> None:
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance (if running)")

    def reset(self) -> None:

        def reset_headersv(component_dict: ComponentTypedDict) -> None:
            self.logger.debug("Resetting state of HeaderSV server...")
            if sys.platform == 'win32':
                datadir = Path(os.environ['LOCALAPPDATA']) / "Temp" / "jcl"
            else:
                datadir = Path("/tmp/jcl")

            if datadir.exists():
                shutil.rmtree(datadir)
                os.mkdir(datadir)

        self.plugin_tools.call_for_component_id_or_type(
            self.COMPONENT_NAME, callable=reset_headersv)
        self.logger.info("Reset of HeaderSV completed successfully")

