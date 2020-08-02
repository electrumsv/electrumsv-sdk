import os
import shlex
import subprocess
import sys
from .utils import (
    checkout_branch,
    create_if_not_exist,
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
        create_if_not_exist(self.app_state.run_scripts_dir)
        os.chdir(self.app_state.run_scripts_dir)
        path_to_dapp_example_apps = self.app_state.electrumsv_dir.joinpath("examples").joinpath(
            "applications"
        )
        electrumsv_env_vars = {
            "PYTHONPATH": path_to_dapp_example_apps.__str__(),
        }
        esv_script = self.app_state.electrumsv_dir.joinpath("electrum-sv").__str__()
        make_esv_daemon_script(esv_script, electrumsv_env_vars)
        make_esv_gui_script(esv_script, electrumsv_env_vars)

    def generate_run_script_electrumx(self):
        create_if_not_exist(self.app_state.run_scripts_dir)
        os.chdir(self.app_state.run_scripts_dir)
        electrumx_env_vars = {
            "DB_DIRECTORY": self.app_state.electrumx_data_dir.__str__(),
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
            make_bash_file("electrumx.sh", commandline_string_split, electrumx_env_vars)

    def generate_run_script_status_monitor(self):
        create_if_not_exist(self.app_state.run_scripts_dir)
        os.chdir(self.app_state.run_scripts_dir)

        commandline_string = (
            f"{sys.executable} " f"{self.app_state.status_monitor_dir.joinpath('server.py')}"
        )

        if sys.platform == "win32":
            commandline_string_split = shlex.split(commandline_string, posix=0)
            make_bat_file("status_monitor.bat", commandline_string_split, {})
        elif sys.platform in ["linux", "darwin"]:
            commandline_string_split = shlex.split(commandline_string, posix=1)
            make_bash_file("status_monitor.sh", commandline_string_split, {})

    def install_electrumsv(self, url, branch):
        # Note - this is only so that it works "out-of-the-box". But for development
        # should use a dedicated electrumsv repo and specify it via cli arguments (not implemented)

        if not self.app_state.electrumsv_dir.exists():
            os.chdir(self.app_state.depends_dir.__str__())
            subprocess.run(f"git clone {url}", shell=True, check=True)
            checkout_branch(branch)
            subprocess.run(
                f"{sys.executable} -m pip install -r {self.app_state.electrumsv_requirements_path}"
            )
            subprocess.run(
                f"{sys.executable} -m pip install -r "
                f"{self.app_state.electrumsv_binary_requirements_path} "
            )
        self.generate_run_scripts_electrumsv()

    def install_electrumx(self, url, branch):

        if not self.app_state.electrumx_dir.exists():
            create_if_not_exist(self.app_state.electrumx_dir.__str__())
            create_if_not_exist(self.app_state.electrumx_data_dir.__str__())
            os.chdir(self.app_state.depends_dir.__str__())
            subprocess.run(f"git clone {url}", shell=True, check=True)
            checkout_branch(branch)
        self.generate_run_script_electrumx()

    def install_status_monitor(self):
        self.generate_run_script_status_monitor()

    def install_bitcoin_node(self):
        subprocess.run(f"{sys.executable} -m pip install electrumsv-node", shell=True, check=True)
