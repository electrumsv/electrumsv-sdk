import os
import shlex
import subprocess
import sys

from .components import ComponentOptions
from .utils import (
    checkout_branch,
    make_esv_daemon_script,
    make_esv_gui_script,
    make_bat_file,
    make_bash_file,
)


class InstallTools:
    def __init__(self, app_state: "AppState"):
        self.app_state = app_state

    def generate_run_scripts_electrumsv(self):
        """makes both the daemon script and a script for running the GUI"""
        os.makedirs(self.app_state.run_scripts_dir, exist_ok=True)
        os.chdir(self.app_state.run_scripts_dir)
        path_to_dapp_example_apps = self.app_state.electrumsv_dir.joinpath("examples").joinpath(
            "applications"
        )
        electrumsv_env_vars = {
            "PYTHONPATH": str(path_to_dapp_example_apps),
        }
        esv_script = str(self.app_state.electrumsv_dir.joinpath("electrum-sv"))
        esv_data_dir = self.app_state.electrumsv_data_dir
        port = self.app_state.electrumsv_port
        component_args = \
            self.app_state.component_args if len(self.app_state.component_args) != 0 else None

        print(f"esv_data_dir = {esv_data_dir}")

        if not self.app_state.start_options[ComponentOptions.GUI]:
            make_esv_daemon_script(esv_script, electrumsv_env_vars, esv_data_dir, port,
                component_args)
        else:
            make_esv_gui_script(esv_script, electrumsv_env_vars, esv_data_dir, port,
                component_args)

    def generate_run_script_electrumx(self):
        os.makedirs(self.app_state.run_scripts_dir, exist_ok=True)
        os.chdir(self.app_state.run_scripts_dir)
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

        if sys.platform == "win32":
            commandline_string_split = shlex.split(commandline_string, posix=0)
            make_bat_file("electrumx.bat", commandline_string_split, electrumx_env_vars)
        elif sys.platform in ["linux", "darwin"]:
            commandline_string_split = shlex.split(commandline_string, posix=1)
            filename = "electrumx.sh"
            make_bash_file("electrumx.sh", commandline_string_split, electrumx_env_vars)
            os.system(f"chmod 777 {filename}")

    def generate_run_script_status_monitor(self):
        os.makedirs(self.app_state.run_scripts_dir, exist_ok=True)
        os.chdir(self.app_state.run_scripts_dir)

        commandline_string = (
            f"{sys.executable} " f"{self.app_state.status_monitor_dir.joinpath('server.py')}"
        )

        if sys.platform == "win32":
            commandline_string_split = shlex.split(commandline_string, posix=0)
            make_bat_file("status_monitor.bat", commandline_string_split, {})
        elif sys.platform in ["linux", "darwin"]:
            commandline_string_split = shlex.split(commandline_string, posix=1)
            filename = "status_monitor.sh"
            make_bash_file(filename, commandline_string_split, {})
            os.system(f'chmod 777 {filename}')

    def install_electrumsv(self, url, branch):
        # Note - this is only so that it works "out-of-the-box". But for development
        # should use a dedicated electrumsv repo and specify it via cli arguments (not implemented)

        if not self.app_state.electrumsv_dir.exists():
            os.chdir(self.app_state.depends_dir)
            subprocess.run(f"git clone {url}", shell=True, check=True)
            checkout_branch(branch)
            subprocess.run(
                f"{sys.executable} -m pip install -r {self.app_state.electrumsv_requirements_path}",
                shell=True, check=True)
            subprocess.run(
                f"{sys.executable} -m pip install -r {self.app_state.electrumsv_binary_requirements_path} ",
                shell=True, check=True)

    def install_electrumx(self, url, branch):

        if not self.app_state.electrumx_dir.exists():
            os.makedirs(self.app_state.electrumx_dir, exist_ok=True)
            os.makedirs(self.app_state.electrumx_data_dir, exist_ok=True)
            os.chdir(self.app_state.depends_dir)
            subprocess.run(f"git clone {url}", shell=True, check=True)
            checkout_branch(branch)
        self.generate_run_script_electrumx()

    def install_status_monitor(self):
        self.generate_run_script_status_monitor()

    def install_bitcoin_node(self):
        subprocess.run(f"{sys.executable} -m pip install electrumsv-node", shell=True, check=True)
