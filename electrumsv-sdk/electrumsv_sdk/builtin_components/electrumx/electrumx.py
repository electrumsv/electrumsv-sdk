import asyncio
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict

from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import ImmutableConfig
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import is_remote_repo, get_directory_name, kill_process, is_docker
from electrumsv_sdk.plugin_tools import PluginTools

from .local_tools import LocalTools


class Plugin(AbstractPlugin):

    ELECTRUMX_PORT = os.environ.get(
        "ELECTRUMX_PORT")  # if None -> set by usual deterministic allocation
    DAEMON_URL = os.environ.get("DAEMON_URL") or "http://rpcuser:rpcpassword@127.0.0.1:18332"
    DB_ENGINE = os.environ.get("DB_ENGINE") or "leveldb"
    COIN = os.environ.get("COIN") or "BitcoinSV"
    COST_SOFT_LIMIT = os.environ.get("COST_SOFT_LIMIT") or 0
    COST_HARD_LIMIT = os.environ.get("COST_HARD_LIMIT") or 0
    MAX_SEND = os.environ.get("MAX_SEND") or 10000000
    LOG_LEVEL = os.environ.get("LOG_LEVEL") or "debug"
    NET = os.environ.get("NET") or "regtest"
    ALLOW_ROOT = os.environ.get("ALLOW_ROOT") or 1

    DEFAULT_PORT = 51001
    RESERVED_PORTS = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)
    DEFAULT_REMOTE_REPO = "https://github.com/kyuupichan/electrumx.git"

    def __init__(self, config: ImmutableConfig):
        self.config = config
        self.plugin_tools = PluginTools(self, self.config)
        self.tools = LocalTools(self)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.plugin_tools.get_source_dir(dirname="electrumx")
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
            self.tools.fetch_electrumx(repo, self.config.branch)

        self.tools.packages_electrumx(repo, self.config.branch)

    def start(self):
        """plugin datadir, id, port are allocated dynamically"""
        self.logger.debug(f"Starting RegTest electrumx daemon...")
        if not self.src.exists():
            self.logger.error(f"source code directory does not exist - try 'electrumsv-sdk install "
                              f"{self.COMPONENT_NAME}' to install the plugin first")
            sys.exit(1)

        self.datadir, self.id = self.plugin_tools.allocate_datadir_and_id()
        self.port = self.plugin_tools.allocate_port()
        self.tools.generate_run_script()
        script_path = self.plugin_tools.derive_shell_script_path(self.COMPONENT_NAME)

        # temporary docker workaround - SDK should allow launching components in current terminal
        if is_docker():
            process = self.plugin_tools.run_command_current_shell(script_path)
        else:
            process = self.plugin_tools.spawn_process(f"{script_path}")

        self.component_info = Component(self.id, process.pid, self.COMPONENT_NAME,
            location=str(self.src), status_endpoint="http://127.0.0.1:51001",
            metadata={"DATADIR": str(self.datadir)}, logging_path=None)

    def stop(self):
        """some components require graceful shutdown via a REST API or RPC API but most can use the
        generic 'app_state.kill_component()' function to track down the pid and kill the process."""
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance(s) (if any)")

    def reset(self):
        def reset_electrumx(component_dict: Dict):
            self.logger.debug("Resetting state of RegTest electrumx server...")
            datadir = Path(component_dict.get('metadata').get("DATADIR"))
            if datadir.exists():
                shutil.rmtree(datadir)
                os.mkdir(datadir)
            else:
                os.makedirs(datadir, exist_ok=True)
            self.logger.debug("Reset of RegTest electrumx server completed successfully.")

        self.plugin_tools.call_for_component_id_or_type(
            self.COMPONENT_NAME, callable=reset_electrumx)
        self.logger.debug("Reset of RegTest electrumx completed successfully")

    def status_check(self) -> Optional[bool]:
        """
        True -> ComponentState.RUNNING;
        False -> ComponentState.FAILED;
        None -> skip status monitoring updates (e.g. using app's cli interface transiently)
        """
        is_running = asyncio.run(self.tools.is_electrumx_running())
        return is_running
