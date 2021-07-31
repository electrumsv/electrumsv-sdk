import logging
import os
import subprocess
import sys
import time
from pathlib import Path
import typing
from typing import Optional, Dict
import stringcase

from electrumsv_sdk.utils import get_directory_name, checkout_branch, split_command, \
    append_to_pythonpath
from electrumsv_sdk.constants import REMOTE_REPOS_DIR, NETWORKS, PYTHON_LIB_DIR

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)

if typing.TYPE_CHECKING:
    from .electrumsv import Plugin


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin: 'Plugin'):
        self.plugin = plugin
        self.plugin_tools = self.plugin.plugin_tools
        self.config = plugin.config
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def process_cli_args(self) -> None:
        self.plugin_tools.set_network()

    def is_offline_cli_mode(self) -> bool:
        if len(self.config.component_args) != 0:
            if self.config.component_args[0] in ['create_wallet', 'create_account', '--help']:
                return True
        return False

    def wallet_db_exists(self) -> bool:
        assert self.plugin.datadir is not None  # typing bug
        datadir = self.get_wallet_path_for_network(self.plugin.datadir)
        assert datadir is not None  # typing bug
        if os.path.exists(datadir):
            return True
        time.sleep(3)  # takes a short time for .sqlite file to become visible
        if os.path.exists(datadir):
            return True
        return False

    def fetch_electrumsv(self, url: str, branch: str) -> None:
        # Todo - make this generic with electrumx
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        assert self.plugin.src is not None  # typing bug
        if not self.plugin.src.exists():
            logger.debug(f"Installing electrumsv (url={url})")
            os.chdir(REMOTE_REPOS_DIR)
            subprocess.run(f"git clone {url}", shell=True, check=True)

        elif self.plugin.src.exists():
            os.chdir(self.plugin.src)
            result = subprocess.run(
                f"git config --get remote.origin.url",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.stdout.strip() == url:
                logger.debug(f"ElectrumSV is already installed (url={url})")
                subprocess.run(f"git pull", shell=True, check=True)
                checkout_branch(branch)
            if result.stdout.strip() != url:
                existing_fork = self.plugin.src
                logger.debug(f"Alternate fork of electrumsv is already installed")
                logger.debug(f"Moving existing fork (to '{existing_fork}.bak')")
                logger.debug(f"Installing electrumsv (url={url})")
                os.rename(
                    self.plugin.src,
                    self.plugin.src.with_suffix(".bak"),
                )

    def packages_electrumsv(self, url: str, branch: str) -> None:
        assert self.plugin.src is not None  # typing bug
        os.chdir(self.plugin.src)
        checkout_branch(branch)

        electrumsv_requirements_path = (
            self.plugin.src.joinpath("contrib/deterministic-build/requirements.txt")
        )
        electrumsv_binary_requirements_path = (
            self.plugin.src.joinpath(
                "contrib/deterministic-build/requirements-binaries.txt")
        )

        electrumsv_libs_path = PYTHON_LIB_DIR / self.plugin.COMPONENT_NAME
        cmd1 = f"{sys.executable} -m pip install --target {electrumsv_libs_path} --upgrade " \
               f"-r {electrumsv_requirements_path}"
        cmd2 = f"{sys.executable} -m pip install --target {electrumsv_libs_path} --upgrade " \
               f"-r {electrumsv_binary_requirements_path}"
        process1 = subprocess.Popen(cmd1, shell=True)
        process1.wait()
        process2 = subprocess.Popen(cmd2, shell=True)
        process2.wait()

    def normalize_wallet_name(self, wallet_name: Optional[str]) -> str:
        if wallet_name is not None:
            if not wallet_name.endswith(".sqlite"):
                wallet_name += ".sqlite"
        else:
            wallet_name = "worker1.sqlite"
        return wallet_name

    def feed_commands_to_esv(self, command_string: str) -> str:
        assert self.plugin.src is not None  # typing bug
        esv_launcher = str(self.plugin.src.joinpath("electrum-sv"))
        component_args = split_command(command_string)
        if component_args:
            additional_args = " ".join(component_args)
            line = f"{sys.executable} {esv_launcher} {additional_args}"
            if "--dir" not in component_args:
                line += " " + f"--dir {self.plugin.datadir}"
        return line

    def get_wallet_path_for_network(self, datadir: Path, wallet_name: Optional[str]=None) -> \
            Optional[Path]:
        wallet_name = self.normalize_wallet_name(wallet_name)
        if self.plugin.network == NETWORKS.REGTEST:
            return datadir.joinpath(f"regtest/wallets/{wallet_name}")
        elif self.plugin.network == NETWORKS.TESTNET:
            return datadir.joinpath(f"testnet/wallets/{wallet_name}")
        else:
            return None
        # elif self.plugin.network == NETWORKS.SCALINGTESTNET:
        #     return datadir.joinpath(f"scalingtestnet/wallets/{wallet_name}")
        # elif self.plugin.network == 'mainnet':
        #     logger.error(f"mainnet is not supported at this time")
        #     sys.exit(1)

    def create_wallet(self, datadir: Path, wallet_name: str) -> None:
        try:
            logger.debug("Creating wallet...")
            wallet_name = self.normalize_wallet_name(wallet_name)
            wallet_path = self.get_wallet_path_for_network(datadir, wallet_name)
            assert wallet_path is not None  # typing bug
            os.makedirs(os.path.dirname(wallet_path), exist_ok=True)
            password = "test"

            # New wallet
            network_string = stringcase.spinalcase(self.plugin.network)  # need kebab-case
            command_string = f"create_wallet --wallet {wallet_path} --walletpassword" \
                             f" {password} --portable --no-password-check --{network_string}"
            line = self.feed_commands_to_esv(command_string)
            process = subprocess.Popen(line, shell=True)
            process.wait()
            logger.debug(f"New wallet created at : {wallet_path} ")

            # New account
            command_string = (
                f"create_account --wallet {wallet_path} --walletpassword {password} --portable "
                f"--no-password-check")
            line = self.feed_commands_to_esv(command_string)
            process = subprocess.Popen(line, shell=True)
            process.wait()
            logger.debug(f"New standard (bip32) account created for: '{wallet_path}'")

        except Exception as e:
            logger.exception("unexpected problem creating new wallet")
            raise

    def delete_wallet(self, datadir: Path) -> None:
        esv_wallet_db_directory = datadir.joinpath("regtest/wallets")
        os.makedirs(esv_wallet_db_directory, exist_ok=True)

        try:
            time.sleep(1)
            logger.debug("Deleting wallet...")
            logger.debug(
                "Wallet directory before: %s", os.listdir(esv_wallet_db_directory),
            )
            file_names = os.listdir(esv_wallet_db_directory)
            for file_name in file_names:
                file_path = esv_wallet_db_directory.joinpath(file_name)
                if Path.exists(file_path):
                    os.remove(file_path)
            logger.debug(
                "Wallet directory after: %s", os.listdir(esv_wallet_db_directory),
            )
        except Exception as e:
            logger.exception(e)
            raise

    def generate_command(self) -> typing.Tuple[str, Dict[str, str]]:
        """
        The electrumsv component type can be executed in 1 of 3 ways:
         1) custom script (if args are supplied to the right-hand-side of <component_name>)
         2) daemon script
         3) gui script for running in GUI mode

        NOTE: This is about as complex as it gets!
        """

        assert self.plugin.src is not None
        def get_default_electrumx() -> str:
            if self.plugin.network == NETWORKS.REGTEST:
                return "127.0.0.1:51001:t"
            elif self.plugin.network == NETWORKS.TESTNET:
                return "austecondevserver.app:51002:s"
            else:
                raise NotImplementedError("scaling-testnet and mainnet not yet supported")

        def set_electrumx_server(command: str, connection_string: Optional[str]) -> str:
            if not connection_string:
                command += f"--server={get_default_electrumx()} "
            elif connection_string is not None:
                command += f"--server={connection_string} "
            return command

        network_string = stringcase.spinalcase(self.plugin.network)  # need kebab-case
        command = ""
        env_vars = {"PYTHONUNBUFFERED": "1"}

        esv_launcher = str(self.plugin.src.joinpath("electrum-sv"))
        port = self.plugin.port
        logger.debug(f"esv_datadir = {self.plugin.datadir}")

        # custom script (user-specified arguments are fed to ESV)
        component_args = self.config.component_args if len(self.config.component_args) != 0 else \
            None

        if component_args:
            additional_args = " ".join(component_args)
            command = f"{sys.executable} {esv_launcher} {additional_args}"
            if "--dir" not in component_args:
                command += " " + f"--dir {self.plugin.datadir}"

        # daemon script
        elif not self.config.gui_flag:
            path_to_example_dapps = self.plugin.src.joinpath("examples/applications")
            append_to_pythonpath([path_to_example_dapps])

            command = (
                f"{sys.executable} {esv_launcher} --portable --dir {self.plugin.datadir} "
                f"--{network_string} daemon -dapp restapi --v=debug "
                f"--file-logging "
                f"--restapi --restapi-port={port} --restapi-user rpcuser --restapi-password= "
            )
            connection_string = self.plugin.ELECTRUMX_CONNECTION_STRING
            command = set_electrumx_server(command, connection_string)

        # GUI script
        else:
            command = (
                f"{sys.executable} {esv_launcher} gui --{network_string} --restapi "
                f"--restapi-port={port} --v=debug --file-logging --dir {self.plugin.datadir} "
            )
            command = set_electrumx_server(command,
                connection_string=self.plugin.ELECTRUMX_CONNECTION_STRING)

        return command, env_vars

