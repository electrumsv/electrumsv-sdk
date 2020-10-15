import argparse
import json
import logging
import os
import subprocess
from pathlib import Path
import shutil
import stat
import sys
from typing import Dict, List, Optional

from electrumsv_node import electrumsv_node

from .starters import Starters
from .stoppers import Stoppers
from .constants import DEFAULT_PORT_ELECTRUMSV
from .argparsing import ArgParser
from .components import ComponentName, ComponentOptions, ComponentStore
from .controller import Controller
from .handlers import Handlers
from .reset import Resetters
from .status_monitor_client import StatusMonitorClient

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger("status")
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)


class AppState:
    """Only electrumsv paths are saved to config.json so that 'reset' works on correct wallet."""

    def __init__(self):
        data_dir = None
        if sys.platform == "win32":
            data_dir = Path(os.environ.get("LOCALAPPDATA")) / "ElectrumSV-SDK"
        if data_dir is None:
            data_dir = Path.home() / ".electrumsv-sdk"

        self.electrumsv_sdk_data_dir = data_dir
        self.plugin_dir = Path(MODULE_DIR).joinpath("builtin_components")

        self.component_store = ComponentStore(self)
        self.arparser = ArgParser(self)
        self.starters = Starters(self)
        self.stoppers = Stoppers(self)
        self.controller = Controller(self)
        self.handlers = Handlers(self)
        self.resetters = Resetters(self)
        self.status_monitor_client = StatusMonitorClient(self)

        if sys.platform in ['linux', 'darwin']:
            self.linux_venv_dir = self.electrumsv_sdk_data_dir.joinpath("sdk_venv")
            self.python = self.linux_venv_dir.joinpath("bin").joinpath("python")
            self.starters.run_command_current_shell(
                f"{sys.executable} -m venv {self.linux_venv_dir}")
        else:
            self.python = sys.executable

        # namespaces
        self.NAMESPACE = ""  # 'start', 'stop' or 'reset'

        # Todo - move these into constants under a CLICommands class (or something)
        self.TOP_LEVEL = "top_level"
        self.START = "start"
        self.STOP = "stop"
        self.RESET = "reset"
        self.NODE = "node"
        self.STATUS = "status"

        self.subcmd_map: Dict[str, argparse.ArgumentParser] = {}  # cmd_name: ArgumentParser
        self.subcmd_raw_args_map: Dict[str, List[str]] = {}  # cmd_name: raw arguments
        self.subcmd_parsed_args_map = {}  # cmd_name: parsed arguments
        self.component_args = []  # e.g. store arguments to pass to the electrumsv's cli interface

        self.depends_dir = self.electrumsv_sdk_data_dir.joinpath("sdk_depends")
        self.run_scripts_dir = self.electrumsv_sdk_data_dir.joinpath("run_scripts")
        self.electrumsv_sdk_config_path = self.electrumsv_sdk_data_dir.joinpath("config.json")

        self.sdk_package_dir = Path(MODULE_DIR)
        self.status_monitor_dir = self.sdk_package_dir.joinpath("status_server")
        self.status_monitor_logging_path = self.electrumsv_sdk_data_dir.joinpath("logs").joinpath(
            "status_monitor")
        os.makedirs(self.status_monitor_logging_path, exist_ok=True)

        self.selected_start_component: Optional[ComponentName] = None
        self.selected_stop_component: Optional[ComponentName] = None
        self.selected_reset_component: Optional[ComponentName] = None

        self.start_options: Dict[ComponentName] = {}
        self.node_args = None

        self.start_options[ComponentOptions.NEW] = False
        self.start_options[ComponentOptions.GUI] = False
        self.start_options[ComponentOptions.BACKGROUND] = False
        self.start_options[ComponentOptions.ID] = ""
        self.start_options[ComponentOptions.REPO] = ""
        self.start_options[ComponentOptions.BRANCH] = ""

    def get_id(self, component_name: ComponentName):
        id = self.start_options[ComponentOptions.ID]
        if not id:  # Default component_name
            id = component_name + "1"
        return id

    def save_repo_paths(self):
        """overwrites config.json"""
        config_path = self.electrumsv_sdk_config_path
        with open(config_path, "r") as f:
            data = f.read()
            if data:
                config = json.loads(data)
            else:
                config = {}

        with open(config_path, "w") as f:
            f.write(json.dumps(config, indent=4))

    def purge_prev_installs_if_exist(self):
        def remove_readonly(func, path, excinfo):  # .git is read-only
            os.chmod(path, stat.S_IWRITE)
            func(path)

        if self.depends_dir.exists():
            shutil.rmtree(self.depends_dir, onerror=remove_readonly)
            os.makedirs(self.depends_dir, exist_ok=True)
        if self.run_scripts_dir.exists():
            shutil.rmtree(self.run_scripts_dir, onerror=remove_readonly)
            os.makedirs(self.run_scripts_dir, exist_ok=True)

    def setup_python_venv(self):
        logger.debug("Setting up python virtualenv (linux/unix only)")
        sdk_data_dir = Path.home() / ".electrumsv-sdk"
        linux_venv_dir = sdk_data_dir.joinpath("sdk_venv")
        python = linux_venv_dir.joinpath("bin").joinpath("python3")
        sdk_requirements_path = Path(MODULE_DIR).parent.joinpath("requirements")\
            .joinpath("requirements.txt")
        sdk_requirements_linux_path = Path(MODULE_DIR).parent.joinpath("requirements").joinpath(
            "requirements-linux.txt")
        subprocess.run(f"sudo {python} -m pip install -r {sdk_requirements_path}",
                       shell=True, check=True)
        subprocess.run(f"sudo {python} -m pip install -r {sdk_requirements_linux_path}",
                       shell=True, check=True)

    def handle_first_ever_run(self):
        """nukes previously installed dependencies and .bat/.sh scripts for the first ever run of
        the electrumsv-sdk."""
        try:
            with open(self.electrumsv_sdk_config_path, "r") as f:
                data = f.read()
                if data:
                    config = json.loads(data)
                else:
                    config = {}
        except FileNotFoundError:
            with open(self.electrumsv_sdk_config_path, "w") as f:
                config = {"is_first_run": True}
                f.write(json.dumps(config, indent=4))

        if config.get("is_first_run") or config.get("is_first_run") is None:
            logger.debug(
                "Running SDK for the first time. please wait for configuration to complete..."
            )
            logger.debug("Purging previous server installations (if any)...")
            self.purge_prev_installs_if_exist()
            with open(self.electrumsv_sdk_config_path, "w") as f:
                config = {"is_first_run": False}
                f.write(json.dumps(config, indent=4))

            if sys.platform in ['linux', 'darwin']:
                self.setup_python_venv()

            logger.debug("Purging completed successfully")

            electrumsv_node.reset()

    def init_run_script_dir(self):
        os.makedirs(self.run_scripts_dir, exist_ok=True)
        os.chdir(self.run_scripts_dir)
