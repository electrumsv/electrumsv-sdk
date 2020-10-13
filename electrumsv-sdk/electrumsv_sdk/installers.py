import logging
import os
import subprocess
import sys
import socket
import errno
from pathlib import Path

from .constants import DEFAULT_ID_ELECTRUMSV, DEFAULT_PORT_ELECTRUMSV
from .components import ComponentOptions, ComponentName
from .utils import checkout_branch

logger = logging.getLogger("installers")


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

    def get_component_data_dir_for_id(self, component_name: ComponentName, component_data_dir:
            Path, id=None):
        """to run multiple instances of electrumsv requires multiple data directories (with
        separate lock files)"""
        new = self.app_state.start_options[ComponentOptions.NEW]
        if not id:
            id = self.app_state.start_options[ComponentOptions.ID]

        # autoincrement (electrumsv1 -> electrumsv2 -> electrumsv3...)
        if self.is_new_and_no_id(id, new):
            count = 1
            while True:
                self.app_state.start_options[ComponentOptions.ID] = id = \
                    str(component_name) + str(count)
                new_dir = component_data_dir.joinpath(id)
                if not new_dir.exists():
                    break
                else:
                    count += 1
            logger.debug(f"Using new user-specified electrumsv data dir ({id})")

        elif self.is_new_and_id(id, new):
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            if new_dir.exists():
                logger.debug(f"User-specified electrumsv data directory: {new_dir} already exists ("
                      f"either drop the --new flag or choose a unique identifier).")
            logger.debug(f"Using user-specified electrumsv data dir ({id})")

        elif self.is_not_new_and_id(id, new):
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            if not new_dir.exists():
                logger.debug(f"User-specified electrumsv data directory: {new_dir} does not exist"
                             f" and so will be created anew.")
            logger.debug(f"Using user-specified electrumsv data dir ({id})")

        elif self.is_not_new_and_no_id(id, new):
            id = DEFAULT_ID_ELECTRUMSV
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            logger.debug(f"Using default electrumsv data dir ({DEFAULT_ID_ELECTRUMSV})")

        logger.debug(f"Electrumsv data dir = {new_dir}")
        return new_dir

    def port_is_in_use(self, port) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", port))
            return False
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                logger.debug("Port is already in use")
                return True
            else:
                logger.debug(e)
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
        data_dir = self.get_component_data_dir_for_id(ComponentName.ELECTRUMSV,
            self.app_state.electrumsv_dir)
        port = self.get_electrumsv_port()
        self.app_state.update_electrumsv_data_dir(data_dir, port)

        if not self.app_state.electrumsv_dir.exists():
            logger.debug(f"Installing electrumsv (url={url})")
            self.app_state.install_tools.fetch_electrumsv(url, branch)

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
                logger.debug(f"Electrumsv is already installed (url={url})")
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
                logger.debug(f"Alternate fork of electrumsv is already installed")
                logger.debug(f"Moving existing fork (to '{existing_fork}.bak')")
                logger.debug(f"Installing electrumsv (url={url})")
                os.rename(
                    self.app_state.electrumsv_dir,
                    self.app_state.electrumsv_dir.with_suffix(".bak"),
                )
                self.app_state.install_tools.fetch_electrumsv(url, branch)

    def local_electrumsv(self, repo, branch):
        logger.debug(f"Installing local dependency for {ComponentName.ELECTRUMSV} "
                     f"at path: {repo}")
        assert Path(repo).exists(), f"the path {repo} does not exist!"
        if branch != "":
            subprocess.run(f"git checkout {branch}", shell=True, check=True)
        self.app_state.set_electrumsv_path(Path(repo))
        new_dir = self.get_component_data_dir_for_id(ComponentName.ELECTRUMSV,
            self.app_state.electrumsv_dir)
        port = self.get_electrumsv_port()
        self.app_state.update_electrumsv_data_dir(new_dir, port)

    def local_electrumx(self, repo, branch):
        logger.debug(f"Installing local dependency for {ComponentName.ELECTRUMX} "
                     f"at path: {repo}")
        assert Path(repo).exists(), f"the path {repo} does not exist!"
        if branch != "":
            subprocess.run(f"git checkout {branch}", shell=True, check=True)
        self.electrumx_dir = Path(repo)
        self.electrumx_data_dir = self.electrumx_dir.joinpath("electrumx_data")

    # ----- installation entry points ----- #
    # 1) fetch (as needed) + install packages
    # 2) generate run script

    def electrumsv(self):
        repo = self.app_state.start_options[ComponentOptions.REPO]
        branch = self.app_state.start_options[ComponentOptions.BRANCH]
        if repo == "" or repo.startswith("https://"):  # default
            repo = "https://github.com/electrumsv/electrumsv.git" if repo == "" else repo
            self.app_state.set_electrumsv_path(self.app_state.depends_dir.joinpath("electrumsv"))
            self.remote_electrumsv(repo, branch)
        else:
            self.local_electrumsv(repo, branch)

        self.app_state.install_tools.generate_run_scripts_electrumsv()

    def electrumx(self):
        """--repo and --branch flags affect the behaviour of the 'fetch' step"""
        repo = self.app_state.start_options[ComponentOptions.REPO]
        branch = self.app_state.start_options[ComponentOptions.BRANCH]
        if repo == "" or repo.startswith("https://"):  # default
            repo = "https://github.com/kyuupichan/electrumx.git"
            self.app_state.install_tools.fetch_electrumx(repo, branch)
        else:
            self.local_electrumx(repo, branch)

        self.app_state.install_tools.generate_run_script_electrumx()

    def node(self, branch):
        """this one has a pip installer at https://pypi.org/project/electrumsv-node/ and
        only official releases from pypi are supported"""
        repo = self.app_state.start_options[ComponentOptions.REPO]
        if not repo == "":  # default
            logger.error("ignoring --repo flag for node - not applicable.")

        self.app_state.install_tools.fetch_node()
        # self.app_state.install_tools.generate_run_script_node()  # N/A

    def status_monitor(self):
        """this is a locally hosted sub-repo so there is no 'fetch' step"""
        repo = self.app_state.start_options[ComponentOptions.REPO]
        if not repo == "":  # default
            logger.error("ignoring --repo flag for status_monitor - not applicable.")

        # self.app_state.install_tools.fetch_status_monitor()  # N/A - part of this repo
        self.app_state.install_tools.generate_run_script_status_monitor()

    def whatsonchain(self):
        self.app_state.install_tools.fetch_whatsonchain()
        self.app_state.install_tools.generate_run_script_whatsonchain()

    def indexer(self):
        raise NotImplementedError("electrumsv_indexer installation is not supported yet.")
