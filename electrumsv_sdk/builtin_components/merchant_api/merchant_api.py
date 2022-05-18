import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Set

from electrumsv_sdk.builtin_components._common.utils import download_and_init_postgres, \
    start_postgres, stop_postgres
from electrumsv_sdk.builtin_components.merchant_api.add_node_to_mapi_thread import AddNodeThread
from electrumsv_sdk.sdk_types import AbstractPlugin
from electrumsv_sdk.config import CLIInputs, Config
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import get_directory_name, kill_process
from electrumsv_sdk.plugin_tools import PluginTools

from .install import download_and_install, get_run_path, chmod_exe, MERCHANT_API_VERSION, \
    load_env_vars, prepare_fresh_postgres
from .check_db_config import check_postgres_db, drop_db_on_install


SDK_POSTGRES_PORT = int(os.environ.get('SDK_POSTGRES_PORT', "5432"))
SDK_PORTABLE_MODE = int(os.environ.get('SDK_PORTABLE_MODE', "0"))
SDK_SKIP_POSTGRES_INIT: int = int(os.environ.get('SDK_SKIP_POSTGRES_INIT', "0"))


class Plugin(AbstractPlugin):

    DEFAULT_PORT = 5050
    RESERVED_PORTS: Set[int] = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)

    NODE_HOST = os.environ.get("NODE_HOST") or "127.0.0.1"
    NODE_RPC_PORT = int(os.environ.get("NODE_RPC_PORT") or 18332)
    NODE_RPC_USERNAME = os.environ.get("NODE_RPC_USERNAME") or "rpcuser"
    NODE_RPC_PASSWORD = os.environ.get("NODE_RPC_PASSWORD") or "rpcpassword"
    NODE_ZMQ_PORT = int(os.environ.get("NODE_ZMQ_PORT") or 28332)
    MERCHANT_API_HOST = os.environ.get("MERCHANT_API_HOST") or "127.0.0.1"
    MERCHANT_API_PORT = int(os.environ.get("MERCHANT_API_PORT") or DEFAULT_PORT)

    def __init__(self, cli_inputs: CLIInputs):
        self.cli_inputs = cli_inputs
        self.config = Config()
        self.plugin_tools = PluginTools(self, self.cli_inputs)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.plugin_tools.get_source_dir(dirname="merchant_api")
        self.datadir: Optional[Path] = None  # dynamically allocated
        self.id: Optional[str] = None  # dynamically allocated
        self.port: Optional[int] = None  # dynamically allocated
        self.component_info: Optional[Component] = None
        download_and_init_postgres()  # only if necessary

    def install(self) -> None:
        assert self.src is not None  # typing bug in mypy
        download_and_install(self.src)

        if SDK_SKIP_POSTGRES_INIT != 1:
            if SDK_PORTABLE_MODE == 1:
                # stop_postgres()
                # reset_postgres()
                start_postgres()

            prepare_fresh_postgres()
            drop_db_on_install()
            check_postgres_db()

        self.logger.debug(f"Installed {self.COMPONENT_NAME}")

    def start(self) -> None:
        assert self.src is not None  # typing bug
        if SDK_PORTABLE_MODE == 1:
            download_and_install(self.src)
            start_postgres()

        self.logger.debug(f"Starting Merchant API")
        prepare_fresh_postgres()
        check_postgres_db()

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
        status_endpoint = "http://127.0.0.1:5050/mapi/feeQuote"

        self.add_node_thread = AddNodeThread(mapi_url="http://127.0.0.1:5050", max_wait_time=10)
        self.add_node_thread.start()

        self.plugin_tools.spawn_process(str(command), env_vars=os.environ.copy(), id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            status_endpoint=status_endpoint)

        # will keep trying to add node until mAPI REST API available (up to a limited wait time)
        self.logger.info("Adding node to mAPI instance (if not already added)")
        self.add_node_thread.join()

    def stop(self) -> None:
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)

        if SDK_PORTABLE_MODE == 1:
            assert self.config.DATADIR is not None
            postgres_install_path = self.config.DATADIR / "postgres"

            # Set this environment variable before importing postgres script
            os.environ['SDK_POSTGRES_INSTALL_DIR'] = str(postgres_install_path)
            from .. import _postgres
            if asyncio.run(_postgres.check_running()):
                stop_postgres()

        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance (if running)")

    def reset(self) -> None:
        assert self.src is not None  # typing bug
        self.stop()

        if SDK_PORTABLE_MODE == 1:
            download_and_install(self.src)
            start_postgres()

        prepare_fresh_postgres()
        drop_db_on_install()
        check_postgres_db()
        self.logger.info("Merchant API database reset complete")
