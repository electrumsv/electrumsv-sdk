import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict

from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import is_remote_repo, kill_process, get_directory_name
from electrumsv_sdk.plugin_tools import PluginTools
from electrumsv_sdk.config import ImmutableConfig

from .local_tools import LocalTools


class Plugin(AbstractPlugin):

    # ---------- Environment Variables ---------- #
    ELECTRUMX_HOST = os.environ.get("ELECTRUMX_HOST") or "127.0.0.1"
    ELECTRUMX_PORT = os.environ.get("ELECTRUMX_PORT") or 51001

    # For documentation purposes only (these env vars will be detected by electrumsv too)
    BITCOIN_NODE_HOST = os.environ.get("BITCOIN_NODE_HOST") or "127.0.0.1"
    BITCOIN_NODE_PORT = os.environ.get("BITCOIN_NODE_PORT") or 18332
    BITCOIN_NODE_RPCUSER = os.environ.get("BITCOIN_NODE_RPCUSER") or "rpcuser"
    BITCOIN_NODE_RPCPASSWORD = os.environ.get("BITCOIN_NODE_RPCPASSWORD") or "rpcpassword"
    RESTAPI_HOST = os.environ.get("RESTAPI_HOST")

    DEFAULT_PORT = 9999
    RESERVED_PORTS = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)
    DEFAULT_REMOTE_REPO = "https://github.com/electrumsv/electrumsv.git"

    def __init__(self, config: ImmutableConfig):
        self.config = config
        self.plugin_tools = PluginTools(self, self.config)
        self.tools = LocalTools(self)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.plugin_tools.get_source_dir(dirname="electrumsv")
        self.datadir = None  # dynamically allocated
        self.id = None  # dynamically allocated
        self.port = None  # dynamically allocated
        self.component_info: Optional[Component] = None

    def install(self):
        """required state: source_dir  - which are derivable from 'repo' and 'branch' flags"""
        repo = self.config.repo
        if self.config.repo == "":
            repo = self.DEFAULT_REMOTE_REPO
        if is_remote_repo(repo):
            self.tools.fetch_electrumsv(repo, self.config.branch)

        self.tools.packages_electrumsv(repo, self.config.branch)
        self.logger.debug(f"Installed {self.COMPONENT_NAME}")

    def start(self):
        """plugin datadir, id, port are allocated dynamically"""
        self.logger.debug(f"Starting RegTest electrumsv daemon...")
        if not self.src.exists():
            self.logger.error(f"source code directory does not exist - try 'electrumsv-sdk install "
                              f"{self.COMPONENT_NAME}' to install the plugin first")
            sys.exit(1)

        self.tools.reinstall_conflicting_dependencies()

        self.datadir, self.id = self.plugin_tools.allocate_datadir_and_id()
        self.port = self.plugin_tools.allocate_port()
        self.tools.generate_run_script()
        os.makedirs(self.datadir.joinpath("regtest/wallets"), exist_ok=True)
        if self.tools.is_offline_cli_mode():
            # 'reset' recurses into here...
            script_path = self.plugin_tools.derive_shell_script_path(self.COMPONENT_NAME)
            _process = self.plugin_tools.spawn_process(f"{script_path}")
            return  # skip the unnecessary status updates

        # If daemon or gui mode continue...
        elif not self.tools.wallet_db_exists():
            # reset wallet
            self.tools.delete_wallet(datadir=self.datadir, wallet_name='worker1.sqlite')
            self.tools.create_wallet(datadir=self.datadir, wallet_name='worker1.sqlite')
            if self.tools.wallet_db_exists():
                self.tools.generate_run_script()  # 'reset' mutates shell script
            else:
                self.logger.exception("wallet db creation failed unexpectedly")

        script_path = self.plugin_tools.derive_shell_script_path(self.COMPONENT_NAME)
        process = self.plugin_tools.spawn_process(f"{script_path}")

        logging_path = self.datadir.joinpath("logs")
        metadata = {"config": str(self.datadir.joinpath("regtest/config")),
                    "DATADIR": str(self.datadir)}

        self.component_info = Component(self.id, process.pid, self.COMPONENT_NAME,
            str(self.src), f"http://127.0.0.1:{self.port}", metadata=metadata,
            logging_path=logging_path)

    def stop(self):
        """some components require graceful shutdown via a REST API or RPC API but most can use the
        generic 'plugin_tools.kill_component()' function."""
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance(s) (if any)")

    def reset(self):
        """reset_electrumsv will be called many times for different component ids if applicable"""
        def reset_electrumsv(component_dict: Dict):
            self.logger.debug("Resetting state of RegTest electrumsv server...")
            datadir = Path(component_dict.get('metadata').get("DATADIR"))
            self.tools.delete_wallet(datadir=datadir, wallet_name='worker1.sqlite')
            self.tools.create_wallet(datadir=datadir, wallet_name='worker1.sqlite')

        self.plugin_tools.call_for_component_id_or_type(
            self.COMPONENT_NAME, callable=reset_electrumsv)
        self.logger.debug("Reset of RegTest electrumsv wallet completed successfully")

    def status_check(self) -> Optional[bool]:
        """
        True -> ComponentState.RUNNING;
        False -> ComponentState.FAILED;
        None -> skip status monitoring updates (e.g. using app's cli interface transiently)
        """
        # Offline CLI interface
        if self.tools.is_offline_cli_mode():
            return  # returning None indicates that the process was intentionally run transiently

        is_running = self.plugin_tools.is_component_running_http(
            status_endpoint=self.component_info.status_endpoint,
            retries=5, duration=2, timeout=1.0)
        return is_running
