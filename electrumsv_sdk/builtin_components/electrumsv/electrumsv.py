from functools import partial
import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Tuple, List, Set

from electrumsv_sdk.sdk_types import AbstractPlugin
from electrumsv_sdk.components import Component, ComponentTypedDict, ComponentMetadata
from electrumsv_sdk.utils import is_remote_repo, kill_process, get_directory_name, \
    set_deterministic_electrumsv_seed
from electrumsv_sdk.plugin_tools import PluginTools
from electrumsv_sdk.config import Config

from .local_tools import LocalTools


def extend_start_cli(start_parser: ArgumentParser) -> Tuple[ArgumentParser, List[str]]:
    """if this method is present it allows extension of the start argparser only.
    This occurs dynamically and adds the new cli options as attributes of the Config object"""
    start_parser.add_argument("--regtest", action="store_true", help="run on regtest")
    start_parser.add_argument("--testnet", action="store_true", help="run on testnet")
    start_parser.add_argument("--deterministic-seed", action="store_true", help="use "
        "deterministic seed for wallet")

    # variable names to be pulled from the start_parser
    new_options = ['regtest', 'testnet', 'deterministic_seed']
    return start_parser, new_options


def extend_reset_cli(reset_parser: ArgumentParser) -> Tuple[ArgumentParser, List[str]]:
    """if this method is present it allows extension of the start argparser only.
    This occurs dynamically and adds the new cli options as attributes of the Config object"""
    reset_parser.add_argument("--deterministic-seed", action="store_true", help="use "
        "deterministic seed for wallet")

    # variable names to be pulled from the start_parser
    new_options = ['deterministic_seed']
    return reset_parser, new_options


class Plugin(AbstractPlugin):

    # ---------- Environment Variables ---------- #
    BITCOIN_NETWORK = os.getenv("BITCOIN_NETWORK", "regtest")
    ELECTRUMX_CONNECTION_STRING = os.getenv("ELECTRUMX_CONNECTION_STRING")

    # For documentation purposes only (these env vars will be detected by electrumsv too)
    ELECTRUMSV_ACCOUNT_XPRV = os.getenv("ELECTRUMSV_ACCOUNT_XPRV")
    BITCOIN_NODE_HOST = os.environ.get("BITCOIN_NODE_HOST") or "127.0.0.1"
    BITCOIN_NODE_PORT = os.environ.get("BITCOIN_NODE_PORT") or 18332
    BITCOIN_NODE_RPCUSER = os.environ.get("BITCOIN_NODE_RPCUSER") or "rpcuser"
    BITCOIN_NODE_RPCPASSWORD = os.environ.get("BITCOIN_NODE_RPCPASSWORD") or "rpcpassword"
    RESTAPI_HOST = os.environ.get("RESTAPI_HOST")

    DEFAULT_PORT = 9999
    RESERVED_PORTS: Set[int] = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)
    DEFAULT_REMOTE_REPO = "https://github.com/electrumsv/electrumsv.git"

    def __init__(self, config: Config):
        self.config = config
        self.plugin_tools = PluginTools(self, self.config)
        self.tools = LocalTools(self)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.plugin_tools.get_source_dir(dirname="electrumsv")
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
            self.tools.fetch_electrumsv(repo, self.config.branch)

        self.tools.packages_electrumsv(repo, self.config.branch)
        self.logger.debug(f"Installed {self.COMPONENT_NAME}")

    def start(self) -> None:
        """plugin datadir, id, port are allocated dynamically"""
        self.plugin_tools.modify_pythonpath_for_portability(self.src)

        self.logger.debug(f"Starting RegTest electrumsv daemon...")
        assert self.src is not None
        if not self.src.exists():
            self.logger.error(f"source code directory does not exist - try 'electrumsv-sdk install "
                              f"{self.COMPONENT_NAME}' to install the plugin first")
            sys.exit(1)

        self.tools.process_cli_args()
        self.datadir, self.id = self.plugin_tools.allocate_datadir_and_id()
        self.port = self.plugin_tools.allocate_port()

        logfile = self.plugin_tools.get_logfile_path(self.id)
        metadata = ComponentMetadata(
            config_path=str(self.datadir.joinpath("regtest/config")),
            datadir=str(self.datadir)
        )
        status_endpoint = f"http://127.0.0.1:{self.port}"
        os.makedirs(self.datadir.joinpath("regtest/wallets"), exist_ok=True)
        if self.tools.is_offline_cli_mode():
            # 'reset' recurses into here...
            command, env_vars = self.tools.generate_command()
            self.plugin_tools.spawn_process(command, env_vars=env_vars, id=self.id,
                component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
                status_endpoint=status_endpoint, metadata=metadata)

        if self.tools.wallet_db_exists():
            if self.config.cli_extension_args['deterministic_seed']:
                if self.tools.wallet_db_exists():
                    raise ValueError(f"Cannot set a deterministic seed. This wallet: '{self.id}' "
                        f"already exists. Please try 'electrumsv-sdk reset --deterministic-seed "
                        f"--id={self.id}' or create a new wallet with a new --id.")

        # If daemon or gui mode continue...
        elif not self.tools.wallet_db_exists():
            if self.config.cli_extension_args['deterministic_seed']:
                set_deterministic_electrumsv_seed(self.config.selected_component,
                    self.config.component_id)
            # reset wallet
            self.tools.delete_wallet(datadir=self.datadir)
            self.tools.create_wallet(datadir=self.datadir, wallet_name='worker1.sqlite')
            if not self.tools.wallet_db_exists():
                self.logger.exception("wallet db creation failed unexpectedly")

        command, env_vars = self.tools.generate_command()
        self.plugin_tools.spawn_process(command, env_vars=env_vars, id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            status_endpoint=status_endpoint, metadata=metadata)

    def stop(self) -> None:
        """some components require graceful shutdown via a REST API or RPC API but most can use the
        generic 'plugin_tools.kill_component()' function."""
        is_new_terminal = not (self.config.inline_flag or self.config.background_flag)
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME,
            callable=partial(kill_process, graceful_wait_period=5.0,
                is_new_terminal=is_new_terminal))
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance (if running)")

    def reset(self) -> None:
        """
        reset_electrumsv will be called many times for different component ids if applicable.
        - the reset entrypoint is only relevant for RegTest
        """
        self.plugin_tools.modify_pythonpath_for_portability(self.src)

        def reset_electrumsv(component_dict: ComponentTypedDict) -> None:
            self.logger.debug("Resetting state of RegTest electrumsv server...")

            # reset is sometimes used with no args and so the --deterministic-seed extension
            # doesn't take effect
            if hasattr(self.config, 'deterministic_seed'):
                if self.config.cli_extension_args['deterministic_seed']:
                    set_deterministic_electrumsv_seed(self.config.selected_component,
                        self.id)
            metadata = component_dict.get('metadata', {})
            assert metadata is not None  # typing bug
            self.datadir = Path(metadata["datadir"])
            self.id = component_dict.get('id')
            self.tools.delete_wallet(datadir=self.datadir)
            self.tools.create_wallet(datadir=self.datadir, wallet_name='worker1.sqlite')

        self.plugin_tools.call_for_component_id_or_type(
            self.COMPONENT_NAME, callable=reset_electrumsv)
        self.logger.info("Reset of RegTest electrumsv wallet completed successfully")
