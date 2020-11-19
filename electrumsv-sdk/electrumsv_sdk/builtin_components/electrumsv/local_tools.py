import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from electrumsv_sdk.utils import get_directory_name, checkout_branch, split_command
from electrumsv_sdk.config import ImmutableConfig
from electrumsv_sdk.constants import REMOTE_REPOS_DIR


COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin):
        self.plugin = plugin
        self.config: ImmutableConfig = plugin.config

    def reinstall_conflicting_dependencies(self):
        if sys.platform == 'win32':
            cmd1 = f"{sys.executable} -m pip install --user aiohttp==3.6.2"
        elif sys.platform in ['linux', 'darwin']:
            cmd1 = f"{sys.executable} -m pip install aiohttp==3.6.2"
        process1 = subprocess.Popen(cmd1, shell=True)
        process1.wait()

    def is_offline_cli_mode(self):
        if len(self.config.component_args) != 0:
            if self.config.component_args[0] in ['create_wallet', 'create_account', '--help']:
                return True
        return False

    def wallet_db_exists(self):
        if os.path.exists(self.plugin.datadir.joinpath("regtest/wallets/worker1.sqlite")):
            return True
        time.sleep(3)  # takes a short time for .sqlite file to become visible
        if os.path.exists(self.plugin.datadir.joinpath("regtest/wallets/worker1.sqlite")):
            return True
        return False

    def fetch_electrumsv(self, url, branch):
        # Todo - make this generic with electrumx
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
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

    def packages_electrumsv(self, url, branch):
        os.chdir(self.plugin.src)
        checkout_branch(branch)

        electrumsv_requirements_path = (
            self.plugin.src.joinpath("contrib/deterministic-build/requirements.txt")
        )
        electrumsv_binary_requirements_path = (
            self.plugin.src.joinpath(
                "contrib/deterministic-build/requirements-binaries.txt")
        )

        if sys.platform == 'win32':
            cmd1 = f"{sys.executable} -m pip install --user --upgrade -r " \
                   f"{electrumsv_requirements_path}"
            cmd2 = f"{sys.executable} -m pip install --user --upgrade -r " \
                   f"{electrumsv_binary_requirements_path}"
        elif sys.platform in ['linux', 'darwin']:
            cmd1 = f"{sys.executable} -m pip install --user --upgrade -r " \
                   f"{electrumsv_requirements_path}"
            cmd2 = f"{sys.executable} -m pip install --user --upgrade -r " \
                   f"{electrumsv_binary_requirements_path}"

        process1 = subprocess.Popen(cmd1, shell=True)
        process1.wait()
        process2 = subprocess.Popen(cmd2, shell=True)
        process2.wait()

    def normalize_wallet_name(self, wallet_name: str):
        if wallet_name is not None:
            if not wallet_name.endswith(".sqlite"):
                wallet_name += ".sqlite"
        else:
            wallet_name = "worker1.sqlite"
        return wallet_name

    def feed_commands_to_esv(self, command_string):
        esv_launcher = str(self.plugin.src.joinpath("electrum-sv"))
        esv_datadir = self.plugin.datadir
        component_args = split_command(command_string)
        if component_args:
            additional_args = " ".join(component_args)
            line = f"{sys.executable} {esv_launcher} {additional_args}"
            if "--dir" not in component_args:
                line += " " + f"--dir {esv_datadir}"
        return line

    def create_wallet(self, datadir: Path, wallet_name: str = None):
        try:
            logger.debug("Creating wallet...")
            wallet_name = self.normalize_wallet_name(wallet_name)
            wallet_path = datadir.joinpath(f"regtest/wallets/{wallet_name}")
            password = "test"

            # New wallet
            command_string = f"create_wallet --wallet {wallet_path} --walletpassword" \
                             f" {password} --portable --no-password-check"
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

    def delete_wallet(self, datadir: Path, wallet_name: str = None):
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

    def generate_run_script(self):
        """
        The electrumsv component type can be executed in 1 of 3 ways:
         1) custom script (if args are supplied to the right-hand-side of <component_name>)
         2) daemon script
         3) gui script for running in GUI mode

        NOTE: This is about as complex as it gets!
        """
        esv_launcher = str(self.plugin.src.joinpath("electrum-sv"))
        port = self.plugin.port
        logger.debug(f"esv_datadir = {self.plugin.datadir}")

        # custom script (user-specified arguments are fed to ESV)
        component_args = self.config.component_args if len(self.config.component_args) != 0 else \
            None

        if component_args:
            additional_args = " ".join(component_args)
            line1 = f"{sys.executable} {esv_launcher} {additional_args}"
            if "--dir" not in component_args:
                line1 += " " + f"--dir {self.plugin.datadir}"

            lines = [line1]

        # daemon script
        elif not self.config.gui_flag:
            path_to_example_dapps = self.plugin.src.joinpath("examples/applications")
            line1 = f"set PYTHONPATH={path_to_example_dapps}"
            if sys.platform in {'linux', 'darwin'}:
                line1 = f"export PYTHONPATH={path_to_example_dapps}"

            line2 = (
                f"{sys.executable} {esv_launcher} --portable --dir {self.plugin.datadir} "
                f"--regtest daemon -dapp restapi --v=debug --file-logging --restapi "
                f"--restapi-port={port} --server={self.plugin.ELECTRUMX_HOST}"
                f":{self.plugin.ELECTRUMX_PORT}:t "
                f"--restapi-user rpcuser --restapi-password= "
            )
            lines = [line1, line2]

        # GUI script
        else:
            line1 = (
                f"{sys.executable} {esv_launcher} gui --regtest --restapi "
                f"--restapi-port={port} --v=debug --file-logging "
                f"--server={self.plugin.ELECTRUMX_HOST}:{self.plugin.ELECTRUMX_PORT}:t "
                f"--dir {self.plugin.datadir}"
            )
            lines = [line1]
        self.plugin.plugin_tools.make_shell_script_for_component(list_of_shell_commands=lines,
            component_name=COMPONENT_NAME)
