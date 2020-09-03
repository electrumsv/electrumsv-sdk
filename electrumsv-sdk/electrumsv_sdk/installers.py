import logging
import os
import subprocess
import sys
import socket
import errno

from .constants import DEFAULT_ID_ELECTRUMSV, DEFAULT_PORT_ELECTRUMSV
from .components import ComponentOptions
from .utils import checkout_branch

logger = logging.getLogger("install-handlers")


class Installers:
    def __init__(self, app_state):
        self.app_state = app_state

    def is_new_and_no_id(self, id, new) -> bool:
        return id == "" and new

    def is_new_and_id(self, id, new) -> bool:
        return id != "" and new

    def is_not_new_and_no_id(self, id, new) -> bool:
        return id == "" and not new

    def is_not_new_and_id(self, id, new) -> bool:
        return id != "" and not new

    def get_electrumsv_data_dir(self):
        """to run multiple instances of electrumsv requires multiple data directories (with
        separate lock files)"""
        new = self.app_state.start_options[ComponentOptions.NEW]
        id = self.app_state.start_options[ComponentOptions.ID]

        # autoincrement (electrumsv1 -> electrumsv2 -> electrumsv3...)
        if self.is_new_and_no_id(id, new):
            count = 1
            while True:
                self.app_state.start_options[ComponentOptions.ID] = id = "electrumsv" + str(count)
                new_dir = self.app_state.electrumsv_dir.joinpath(id)
                if not new_dir.exists():
                    break
                else:
                    count += 1
            logger.debug(f"using new user-specified electrumsv data dir ({id})")

        elif self.is_new_and_id(id, new):
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            if new_dir.exists():
                print(f"user-specified electrumsv data directory: {new_dir} already exists ("
                      f"either drop the --new flag or choose a unique identifier).")
            logger.debug(f"using user-specified electrumsv data dir ({id})")

        elif self.is_not_new_and_id(id, new):
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            if not new_dir.exists():
                print(f"user-specified electrumsv data directory: {new_dir} does not exist ("
                      f"either use the --new flag or choose a pre-existing id.")
            logger.debug(f"using user-specified electrumsv data dir ({id})")

        elif self.is_not_new_and_no_id(id, new):
            id = DEFAULT_ID_ELECTRUMSV
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            logger.debug(f"using default electrumsv data dir ({DEFAULT_ID_ELECTRUMSV})")

        logger.debug(f"electrumsv data dir = {new_dir}")
        return new_dir

    def port_is_in_use(self, port) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", port))
            return False
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                print("Port is already in use")
                return True
            else:
                print(e)
        s.close()

    def get_electrumsv_port(self):
        """any port that is not currently in use"""
        port = DEFAULT_PORT_ELECTRUMSV
        while True:
            if self.port_is_in_use(port):
                port += 1
            else:
                break
        return port

    def remote_electrumsv(self, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        new_dir = self.get_electrumsv_data_dir()
        port = self.get_electrumsv_port()
        self.app_state.update_electrumsv_data_dir(new_dir, port)

        if not self.app_state.electrumsv_dir.exists():
            print(f"- installing electrumsv (url={url})")
            self.app_state.install_tools.install_electrumsv(url, branch)

        elif self.app_state.electrumsv_dir.exists():
            os.chdir(self.app_state.electrumsv_dir)
            result = subprocess.run(
                f"git config --get remote.origin.url",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.stdout.strip() == url:
                print(f"- electrumsv is already installed (url={url})")
                checkout_branch(branch)
                subprocess.run(f"git pull", shell=True, check=True)
                subprocess.run(
                    f"{sys.executable} -m pip install -r "
                    f"{self.app_state.electrumsv_requirements_path}",
                    shell=True,
                    check=True,
                )
                subprocess.run(
                    f"{sys.executable} -m pip install -r "
                    f"{self.app_state.electrumsv_binary_requirements_path}",
                    shell=True,
                    check=True,
                )
            if result.stdout.strip() != url:
                existing_fork = self.app_state.electrumsv_dir
                print(f"- alternate fork of electrumsv is already installed")
                print(f"- moving existing fork (to '{existing_fork}.bak')")
                print(f"- installing electrumsv (url={url})")
                os.rename(
                    self.app_state.electrumsv_dir,
                    self.app_state.electrumsv_dir.with_suffix(".bak"),
                )
                self.app_state.install_tools.install_electrumsv(url, branch)

        os.makedirs(self.app_state.electrumsv_regtest_wallets_dir, exist_ok=True)
        self.app_state.install_tools.generate_run_scripts_electrumsv()

    def local_electrumsv(self, url, branch):
        new_dir = self.get_electrumsv_data_dir()
        port = self.get_electrumsv_port()
        self.app_state.update_electrumsv_data_dir(new_dir, port)

        os.makedirs(self.app_state.electrumsv_regtest_wallets_dir, exist_ok=True)
        self.app_state.install_tools.generate_run_scripts_electrumsv()

    def remote_electrumx(self, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        if not self.app_state.electrumx_dir.exists():
            print(f"- installing electrumx (url={url})")
            self.app_state.install_tools.install_electrumx(url, branch)
        elif self.app_state.electrumx_dir.exists():
            os.chdir(self.app_state.electrumx_dir)
            result = subprocess.run(
                f"git config --get remote.origin.url",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.stdout.strip() == url:
                print(f"- electrumx is already installed (url={url})")
                checkout_branch(branch)
                subprocess.run(f"git pull", shell=True, check=True)
                # Todo - cannot re-install requirements dynamically because of plyvel
                #  awaiting a PR for electrumx

            if result.stdout.strip() != url:
                existing_fork = self.app_state.electrumx_dir
                print(f"- alternate fork of electrumx is already installed")
                print(f"- moving existing fork (to '{existing_fork}.bak')")
                print(f"- installing electrumsv (url={url})")
                os.rename(
                    self.app_state.electrumx_dir,
                    self.app_state.electrumx_dir.with_suffix(".bak"),
                )
                self.app_state.install_tools.install_electrumx(url, branch)

    def local_electrumx(self, path, branch):
        self.app_state.install_tools.generate_run_script_electrumx()

    def node(self, branch):
        """this one has a pip installer at https://pypi.org/project/electrumsv-node/"""
        self.app_state.install_tools.install_bitcoin_node()

    def status_monitor(self):
        """purely for generating the .bat / .sh script"""
        self.app_state.install_tools.install_status_monitor()
