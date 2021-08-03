import logging
import os
import sys
from pathlib import Path
from typing import Optional, Set

from electrumsv_sdk.sdk_types import AbstractPlugin
from electrumsv_sdk.config import Config
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import get_directory_name, kill_process
from electrumsv_sdk.plugin_tools import PluginTools

from .install import download_and_install, load_env_vars, get_run_path, chmod_exe, \
    MERCHANT_API_VERSION
from .check_db_config import check_postgres_db, drop_db_on_install


class Plugin(AbstractPlugin):

    DEFAULT_PORT = 45111
    RESERVED_PORTS: Set[int] = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)

    NODE_HOST = os.environ.get("NODE_HOST") or "127.0.0.1"
    NODE_RPC_PORT = int(os.environ.get("NODE_RPC_PORT") or 18332)
    NODE_RPC_USERNAME = os.environ.get("NODE_RPC_USERNAME") or "rpcuser"
    NODE_RPC_PASSWORD = os.environ.get("NODE_RPC_PASSWORD") or "rpcpassword"
    NODE_ZMQ_PORT = int(os.environ.get("NODE_ZMQ_PORT") or 28332)
    MERCHANT_API_HOST = os.environ.get("MERCHANT_API_HOST") or "127.0.0.1"
    MERCHANT_API_PORT = int(os.environ.get("MERCHANT_API_PORT") or DEFAULT_PORT)

    def __init__(self, config: Config):
        self.config = config
        self.plugin_tools = PluginTools(self, self.config)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.plugin_tools.get_source_dir(dirname="merchant_api")
        self.datadir: Optional[Path] = None  # dynamically allocated
        self.id: Optional[str] = None  # dynamically allocated
        self.port: Optional[int] = None  # dynamically allocated
        self.component_info: Optional[Component] = None

    def install(self) -> None:
        assert self.src is not None  # typing bug
        download_and_install(self.src)
        drop_db_on_install()
        check_postgres_db()
        self.logger.debug(f"Installed {self.COMPONENT_NAME}")

    def start(self) -> None:
        self.logger.debug(f"Starting Merchant API")
        check_postgres_db()
        assert self.src is not None  # typing bug
        if not self.src.exists():
            self.logger.error(f"source code directory does not exist - try 'electrumsv-sdk install "
                              f"{self.COMPONENT_NAME}' to install the plugin first")
            sys.exit(1)

        self.id = self.plugin_tools.get_id(self.COMPONENT_NAME)
        self.port = self.MERCHANT_API_PORT
        # The primary reason we need this to be the current directory is so that the `settings.conf`
        # file is directly accessible to the MAPI executable (it should look there first).
        os.chdir(self.src)

        # EXE RUN MODE
        load_env_vars()
        try:
            chmod_exe(self.src)
            command = get_run_path(self.src)
        except FileNotFoundError:
            self.logger.error(f"Could not find version: {MERCHANT_API_VERSION} of the "
                f"merchant_api. Have you tried re-running 'electrumsv-sdk install merchant_api' to "
                f"pull the latest version?")
            return

        logfile = self.plugin_tools.get_logfile_path(self.id)
        status_endpoint = "http://127.0.0.1:45111/mapi/feeQuote"

        self.plugin_tools.spawn_process(str(command), env_vars=os.environ.copy(), id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            status_endpoint=status_endpoint)

    def stop(self) -> None:
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance (if running)")

    def reset(self) -> None:
        self.logger.info("resetting Merchant API is not applicable")
