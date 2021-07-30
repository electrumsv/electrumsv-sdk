import logging
import os
import shutil
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Tuple, List, Set

from electrumsv_sdk.sdk_types import AbstractPlugin
from electrumsv_sdk.config import Config
from electrumsv_sdk.components import Component, ComponentTypedDict
from electrumsv_sdk.utils import is_remote_repo, get_directory_name, kill_process
from electrumsv_sdk.plugin_tools import PluginTools

from .local_tools import LocalTools


def extend_start_cli(start_parser: ArgumentParser) -> Tuple[ArgumentParser, List[str]]:
    """if this method is present it allows extension of the start argparser only.
    This occurs dynamically and adds the new cli options as attributes of the Config object"""
    start_parser.add_argument("--regtest", action="store_true", help="run on regtest")
    start_parser.add_argument("--testnet", action="store_true", help="run on testnet")

    # variable names to be pulled from the start_parser
    new_options = ['regtest', 'testnet']
    return start_parser, new_options


class Plugin(AbstractPlugin):

    BITCOIN_NETWORK = os.getenv("BITCOIN_NETWORK", "regtest")  # 'BITCOIN_NETWORK' is the SDK global
    BITCOIN_NETWORK = os.getenv("NET", BITCOIN_NETWORK)  # ElectrumX documentation uses "NET"

    ELECTRUMX_PORT = os.environ.get(
        "ELECTRUMX_PORT")  # if None -> set by usual deterministic allocation
    DAEMON_URL = os.environ.get("DAEMON_URL") or "http://rpcuser:rpcpassword@127.0.0.1:18332"
    DB_ENGINE = os.environ.get("DB_ENGINE") or "leveldb"
    COIN = os.environ.get("COIN") or "BitcoinSV"
    COST_SOFT_LIMIT = os.environ.get("COST_SOFT_LIMIT") or 0
    COST_HARD_LIMIT = os.environ.get("COST_HARD_LIMIT") or 0
    MAX_SEND = os.environ.get("MAX_SEND") or 10000000
    LOG_LEVEL = os.environ.get("LOG_LEVEL") or "debug"
    ALLOW_ROOT = os.environ.get("ALLOW_ROOT") or 1

    DEFAULT_PORT = 51001
    RESERVED_PORTS: Set[int] = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)
    DEFAULT_REMOTE_REPO = "https://github.com/kyuupichan/electrumx.git"

    def __init__(self, config: Config) -> None:
        self.config = config
        self.plugin_tools = PluginTools(self, self.config)
        self.tools = LocalTools(self)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.plugin_tools.get_source_dir(dirname="electrumx")
        self.datadir = None  # dynamically allocated
        self.id = None  # dynamically allocated
        self.port = None  # dynamically allocated
        self.component_info: Optional[Component] = None

        self.network = self.BITCOIN_NETWORK

    def install(self) -> None:
        """required state: source_dir  - which are derivable from 'repo' and 'branch' flags"""
        self.plugin_tools.modify_pythonpath_for_portability(self.src)

        repo = self.config.repo
        if self.config.repo == "":
            repo = self.DEFAULT_REMOTE_REPO
        if is_remote_repo(repo):
            self.tools.fetch_electrumx(repo, self.config.branch)

        self.tools.packages_electrumx(repo, self.config.branch)

    def start(self) -> None:
        """plugin datadir, id, port are allocated dynamically"""
        self.logger.debug(f"Starting RegTest electrumx daemon...")
        assert self.src is not None  # typing bug
        if not self.src.exists():
            self.logger.error(f"source code directory does not exist - try 'electrumsv-sdk install "
                              f"{self.COMPONENT_NAME}' to install the plugin first")
            sys.exit(1)

        self.plugin_tools.modify_pythonpath_for_portability(self.src)
        self.datadir, self.id = self.plugin_tools.allocate_datadir_and_id()
        self.port = self.plugin_tools.allocate_port()
        self.tools.process_cli_args()  # cli args may override network in env vars

        command = f"{sys.executable} {self.src.joinpath('electrumx_server')}"
        env_vars = {
            "PYTHONUNBUFFERED": "1",
            "SERVICES": f"{f'tcp://:{self.port},rpc://'}",
            "DB_DIRECTORY": f"{self.datadir}",
            "DAEMON_URL": f"{self.DAEMON_URL}",
            "DB_ENGINE": f"{self.DB_ENGINE}",
            "COIN": f"{self.COIN}",
            "COST_SOFT_LIMIT": f"{self.COST_SOFT_LIMIT}",
            "COST_HARD_LIMIT": f"{self.COST_HARD_LIMIT}",
            "MAX_SEND": f"{self.MAX_SEND}",
            "LOG_LEVEL": f"{self.LOG_LEVEL}",
            "NET": f"{self.network}",
            "ALLOW_ROOT": f"{self.ALLOW_ROOT}",
        }
        logfile = self.plugin_tools.get_logfile_path(self.id)
        self.plugin_tools.spawn_process(command, env_vars=env_vars, id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            status_endpoint=f"http://127.0.0.1:{self.port}",
            metadata={"datadir": str(self.datadir), "rpcport": 8000})

    def stop(self) -> None:
        """some components require graceful shutdown via a REST API or RPC API but most can use the
        generic 'app_state.kill_component()' function to track down the pid and kill the process."""
        def stop_electrumx(component_dict: ComponentTypedDict) -> None:
            metadata = component_dict.get("metadata", {})
            assert metadata is not None  # typing bug
            rpcport = metadata.get("rpcport")
            if not rpcport:
                raise Exception("rpcport data not found")
            was_successful = self.tools.run_coroutine_ipython_friendly(self.tools.stop_electrumx)
            if not was_successful:
                self.logger.debug("Unable to connect to ElectrumX - is it already stopped?")
                kill_process(component_dict)

        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME,
            callable=stop_electrumx)
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance (if running)")

    def reset(self) -> None:
        def reset_electrumx(component_dict: ComponentTypedDict) -> None:
            self.logger.debug("Resetting state of RegTest electrumx server...")
            metadata = component_dict.get('metadata', {})
            assert metadata is not None  # typing bug
            datadir = Path(metadata["datadir"])
            if datadir.exists():
                shutil.rmtree(datadir)
                os.mkdir(datadir)
            else:
                os.makedirs(datadir, exist_ok=True)
            self.logger.debug("Reset of RegTest electrumx server completed successfully.")

        self.plugin_tools.call_for_component_id_or_type(
            self.COMPONENT_NAME, callable=reset_electrumx)
        self.logger.info("Reset of RegTest electrumx completed successfully")
