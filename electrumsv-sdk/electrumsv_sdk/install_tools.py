import logging
import os
import subprocess
import sys
from pathlib import Path

from .installers import Installers
from .components import ComponentOptions, ComponentName
from .utils import (
    checkout_branch,
    make_esv_custom_script,
    make_esv_daemon_script,
    make_esv_gui_script,
    make_shell_script_for_component,
)

logger = logging.getLogger("install-tools")


class InstallTools:
    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.installers = Installers(self.app_state)

    def install_from_local_repo(self, package_name, path, branch):
        try:
            logger.debug(f"Installing local dependency for {package_name} at path: {path}")
            assert Path(path).exists(), f"the path {path} to {package_name} does not exist!"
            if branch != "":
                subprocess.run(f"git checkout {branch}", shell=True, check=True)

            if package_name == ComponentName.ELECTRUMSV:
                self.installers.local_electrumsv(path, branch)

            if package_name == ComponentName.ELECTRUMX:
                self.installers.local_electrumx(path, branch)

        except Exception as e:
            raise e

    def install_from_remote_repo(self, package_name, url, branch):
        logger.debug(f"Installing remote dependency for {package_name} at {url}")

        if package_name == ComponentName.ELECTRUMSV:
            self.installers.remote_electrumsv(url, branch)

        if package_name == ComponentName.ELECTRUMX:
            self.installers.remote_electrumx(url, branch)

        if package_name == ComponentName.NODE:
            self.installers.node(branch)

    # ----- SCRIPT GENERATORS ----- #

    def init_run_script_dir(self):
        os.makedirs(self.app_state.run_scripts_dir, exist_ok=True)
        os.chdir(self.app_state.run_scripts_dir)

    def generate_run_scripts_electrumsv(self):
        """makes both the daemon script and a script for running the GUI"""
        self.init_run_script_dir()
        path_to_dapp_example_apps = self.app_state.electrumsv_dir.joinpath("examples").joinpath(
            "applications"
        )
        esv_env_vars = {
            "PYTHONPATH": str(path_to_dapp_example_apps),
        }
        esv_script = str(self.app_state.electrumsv_dir.joinpath("electrum-sv"))
        esv_data_dir = self.app_state.electrumsv_data_dir
        port = self.app_state.electrumsv_port
        component_args = \
            self.app_state.component_args if len(self.app_state.component_args) != 0 else None

        logger.debug(f"esv_data_dir = {esv_data_dir}")

        base_cmd = (f"{sys.executable} {esv_script}")
        if component_args:
            make_esv_custom_script(base_cmd, esv_env_vars, component_args, esv_data_dir)
        elif not self.app_state.start_options[ComponentOptions.GUI]:
            make_esv_daemon_script(base_cmd, esv_env_vars, esv_data_dir, port)
        else:
            make_esv_gui_script(base_cmd, esv_env_vars, esv_data_dir, port)

    def generate_run_script_electrumx(self):
        self.init_run_script_dir()
        electrumx_env_vars = {
            "DB_DIRECTORY": str(self.app_state.electrumx_data_dir),
            "DAEMON_URL": "http://rpcuser:rpcpassword@127.0.0.1:18332",
            "DB_ENGINE": "leveldb",
            "SERVICES": "tcp://:51001,rpc://",
            "COIN": "BitcoinSV",
            "COST_SOFT_LIMIT": "0",
            "COST_HARD_LIMIT": "0",
            "MAX_SEND": "10000000",
            "LOG_LEVEL": "debug",
            "NET": "regtest",
        }

        commandline_string = (
            f"{sys.executable} {self.app_state.electrumx_dir.joinpath('electrumx_server')}"
        )
        make_shell_script_for_component(ComponentName.ELECTRUMX, commandline_string,
            electrumx_env_vars)

    def generate_run_script_status_monitor(self):
        self.init_run_script_dir()
        commandline_string = (
            f"{sys.executable} " f"{self.app_state.status_monitor_dir.joinpath('server.py')}"
        )
        make_shell_script_for_component(ComponentName.STATUS_MONITOR, commandline_string, {})

    def generate_run_script_whatsonchain(self):
        self.init_run_script_dir()

        commandline_string1 = f"cd {self.app_state.woc_dir}\n"
        commandline_string2 = f"call npm start\n" if sys.platform == "win32" else f"npm start\n"
        separate_lines = [commandline_string1, commandline_string2]
        make_shell_script_for_component(ComponentName.WHATSONCHAIN,
                                        commandline_string=None, env_vars=None, multiple_lines=separate_lines)

    def setup_paths_and_shell_scripts_electrumsv(self):
        repo = self.app_state.start_options[ComponentOptions.REPO]
        branch = self.app_state.start_options[ComponentOptions.BRANCH]
        if repo == "":  # default
            repo_default = "https://github.com/electrumsv/electrumsv.git"
            self.app_state.set_electrumsv_path(self.app_state.depends_dir.joinpath("electrumsv"))
            self.install_from_remote_repo(ComponentName.ELECTRUMSV, repo_default, branch)
        elif repo.startswith("https://"):
            self.app_state.set_electrumsv_path(self.app_state.depends_dir.joinpath("electrumsv"))
            self.install_from_remote_repo(ComponentName.ELECTRUMSV, repo, branch)
        else:
            self.app_state.set_electrumsv_path(Path(repo))
            self.install_from_local_repo(ComponentName.ELECTRUMSV, repo, branch)

    # ----- INSTALL FUNCTIONS ----- #

    def fetch_electrumsv(self, url, branch):
        # Note - this is only so that it works "out-of-the-box". But for development
        # should use a dedicated electrumsv repo and specify it via cli arguments (not implemented)
        if not self.app_state.electrumsv_dir.exists():
            os.chdir(self.app_state.depends_dir)
            subprocess.run(f"git clone {url}", shell=True, check=True)

            os.chdir(self.app_state.electrumsv_dir)
            checkout_branch(branch)

            process1 = subprocess.Popen(
                f"{sys.executable} -m pip install --user -r"
                f" {self.app_state.electrumsv_requirements_path}",
                shell=True)
            process1.wait()
            process2 = subprocess.Popen(
                f"{sys.executable} -m pip install --user -r"
                f" {self.app_state.electrumsv_binary_requirements_path} ",
                shell=True)
            process2.wait()

    def fetch_electrumx(self, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        if not self.app_state.electrumx_dir.exists():
            logger.debug(f"Installing electrumx (url={url})")

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
                logger.debug(f"Electrumx is already installed (url={url})")
                checkout_branch(branch)
                subprocess.run(f"git pull", shell=True, check=True)
                # Todo - cannot re-install requirements dynamically because of plyvel
                #  awaiting a PR for electrumx

            if result.stdout.strip() != url:
                existing_fork = self.app_state.electrumx_dir
                logger.debug(f"Alternate fork of electrumx is already installed")
                logger.debug(f"Moving existing fork (to '{existing_fork}.bak')")
                logger.debug(f"Installing electrumsv (url={url})")
                os.rename(
                    self.app_state.electrumx_dir,
                    self.app_state.electrumx_dir.with_suffix(".bak"),
                )

        if not self.app_state.electrumx_dir.exists():
            os.makedirs(self.app_state.electrumx_dir, exist_ok=True)
            os.makedirs(self.app_state.electrumx_data_dir, exist_ok=True)
            os.chdir(self.app_state.depends_dir)
            subprocess.run(f"git clone {url}", shell=True, check=True)

            os.chdir(self.app_state.electrumx_dir)
            checkout_branch(branch)

    def fetch_status_monitor(self):
        pass

    def fetch_node(self):
        subprocess.run(f"{sys.executable} -m pip install electrumsv-node", shell=True, check=True)

    def fetch_whatsonchain(self, url="https://github.com/AustEcon/woc-explorer.git", branch=''):

        if not self.app_state.woc_dir.exists():
            os.makedirs(self.app_state.woc_dir, exist_ok=True)
            os.chdir(self.app_state.depends_dir)
            subprocess.run(f"git clone {url}", shell=True, check=True)

            os.chdir(self.app_state.woc_dir)
            checkout_branch(branch)

        os.chdir(self.app_state.woc_dir)
        process = subprocess.Popen("call npm install\n" if sys.platform == "win32"
                       else "npm install\n",
                       shell=True)
        process.wait()
        process = subprocess.Popen("call npm run-script build\n" if sys.platform == "win32"
                       else "npm run-script build\n",
                       shell=True)
        process.wait()
