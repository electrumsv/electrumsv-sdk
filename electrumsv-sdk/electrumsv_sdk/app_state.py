import argparse
import importlib
import json
import logging
import os
import subprocess
import time
from pathlib import Path
import shutil
import stat
import sys
from typing import Dict, List, Optional

import requests
from electrumsv_node import electrumsv_node

from .utils import trace_processes_for_cmd, trace_pid, kill_process
from .constants import ComponentLaunchFailedError
from .argparsing import ArgParser
from .components import ComponentName, ComponentOptions, ComponentStore, ComponentState, Component
from .controller import Controller
from .handlers import Handlers
from .status_monitor_client import StatusMonitorClient

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger("status")
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)
orm_logger = logging.getLogger("peewee")
orm_logger.setLevel(logging.WARNING)


class AppState:
    """Only electrumsv paths are saved to config.json so that 'reset' works on correct wallet."""

    def __init__(self):
        data_dir = None
        if sys.platform == "win32":
            data_dir = Path(os.environ.get("LOCALAPPDATA")) / "ElectrumSV-SDK"
        if data_dir is None:
            data_dir = Path.home() / ".electrumsv-sdk"

        # set main application paths
        self.sdk_home_dir = data_dir
        self.remote_repos_dir = self.sdk_home_dir.joinpath("remote_repos")
        self.shell_scripts_dir = self.sdk_home_dir.joinpath("shell_scripts")
        self.data_dir = self.sdk_home_dir.joinpath("component_datadirs")
        self.logs_dir = self.sdk_home_dir.joinpath("logs")
        self.config_path = self.sdk_home_dir.joinpath("config.json")
        os.makedirs(self.remote_repos_dir, exist_ok=True)
        os.makedirs(self.shell_scripts_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

        self.sdk_package_dir = Path(MODULE_DIR)
        # plugins - 'user_components' overrides 'builtin_components' if there are name clashes
        self.builtin_components_dir = Path(MODULE_DIR).joinpath("builtin_components")
        self.user_components_dir = self.sdk_home_dir.joinpath("user_components")

        self.component_store = ComponentStore(self)
        self.arparser = ArgParser(self)
        self.controller = Controller(self)
        self.handlers = Handlers(self)
        self.status_monitor_client = StatusMonitorClient(self)

        self.component_module = None  # e.g. builtin_components.node.node.py module
        self.component_info: Optional[Component] = None  # dict conversion <-> status_monitor

        if sys.platform in ['linux', 'darwin']:
            self.linux_venv_dir = self.sdk_home_dir.joinpath("sdk_venv")
            self.python = self.linux_venv_dir.joinpath("bin").joinpath("python")
            self.run_command_current_shell(
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

        self.status_monitor_dir = self.sdk_package_dir.joinpath("status_server")
        self.status_monitor_logging_path = self.logs_dir.joinpath("status_monitor")
        os.makedirs(self.status_monitor_logging_path, exist_ok=True)

        self.selected_start_component: Optional[ComponentName] = None
        self.selected_stop_component: Optional[ComponentName] = None
        self.selected_reset_component: Optional[ComponentName] = None

        self.global_cli_flags: Dict[ComponentName] = {}
        self.node_args = None

        # Todo - just make these app_state attributes
        self.global_cli_flags[ComponentOptions.NEW] = False
        self.global_cli_flags[ComponentOptions.GUI] = False
        self.global_cli_flags[ComponentOptions.BACKGROUND] = False
        self.global_cli_flags[ComponentOptions.ID] = ""
        self.global_cli_flags[ComponentOptions.REPO] = ""
        self.global_cli_flags[ComponentOptions.BRANCH] = ""

    def get_id(self, component_name: ComponentName):
        id = self.global_cli_flags[ComponentOptions.ID]
        if not id:  # Default component_name
            id = component_name + "1"
        return id

    def save_repo_paths(self):
        """overwrites config.json"""
        config_path = self.config_path
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

        if self.remote_repos_dir.exists():
            shutil.rmtree(self.remote_repos_dir, onerror=remove_readonly)
            os.makedirs(self.remote_repos_dir, exist_ok=True)
        if self.shell_scripts_dir.exists():
            shutil.rmtree(self.shell_scripts_dir, onerror=remove_readonly)
            os.makedirs(self.shell_scripts_dir, exist_ok=True)

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
            with open(self.config_path, "r") as f:
                data = f.read()
                if data:
                    config = json.loads(data)
                else:
                    config = {}
        except FileNotFoundError:
            with open(self.config_path, "w") as f:
                config = {"is_first_run": True}
                f.write(json.dumps(config, indent=4))

        if config.get("is_first_run") or config.get("is_first_run") is None:
            logger.debug(
                "Running SDK for the first time. please wait for configuration to complete..."
            )
            logger.debug("Purging previous server installations (if any)...")
            self.purge_prev_installs_if_exist()
            with open(self.config_path, "w") as f:
                config = {"is_first_run": False}
                f.write(json.dumps(config, indent=4))

            if sys.platform in ['linux', 'darwin']:
                self.setup_python_venv()

            logger.debug("Purging completed successfully")

            electrumsv_node.reset()

    def init_run_script_dir(self):
        os.makedirs(self.shell_scripts_dir, exist_ok=True)
        os.chdir(self.shell_scripts_dir)

    def is_component_running_http(self, status_endpoint: str, retries:
            int=6, duration: float=1.0, timeout: float=0.5, http_method='get',
            payload: Dict=None, component_name: ComponentName=None) -> bool:

        if not component_name and self.component_info:
            component_name = self.component_info.component_type
        elif not component_name and not self.component_info:
            raise Exception(f"Unknown component_name")

        for sleep_time in [duration] * retries:
            logger.debug(f"Polling {component_name}...")
            try:
                result = getattr(requests, http_method)(status_endpoint, timeout=timeout,
                    data=payload)
                result.raise_for_status()
                return True
            except Exception as e:
                pass

            time.sleep(sleep_time)
        return False

    def derive_shell_script_path(self, component_name):
        script_name = component_name

        if sys.platform == "win32":
            script = self.shell_scripts_dir.joinpath(f"{script_name}.bat")
        elif sys.platform in ("linux", "darwin"):
            script = self.shell_scripts_dir.joinpath(f"{script_name}.sh")
        return script

    def spawn_process(self, command: str):
        if self.global_cli_flags[ComponentOptions.BACKGROUND]:
            return self.spawn_in_background(command)
        else:
            return self.spawn_in_new_console(command)

    def run_command_current_shell(self, command: str):
        subprocess.run(command, shell=True, check=True)

    def run_command_background(self, command: str):
        if sys.platform in ('linux', 'darwin'):
            process_handle = subprocess.Popen(f"nohup {command} &", shell=True,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
            process_handle.wait()
            return process_handle
        elif sys.platform == 'win32':
            logger.info(
                "Running as a background process (without a console window) is not supported "
                "on windows, spawning in a new console window")
            process_handle = subprocess.Popen(
                f"{command}", creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            return process_handle

    def run_command_new_window(self, command: str):
        if sys.platform in ('linux', 'darwin'):
            # todo gnome-terminal part will not work cross-platform for spawning new terminals
            process_handle = subprocess.Popen(f"gnome-terminal -- {command}", shell=True,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process_handle.wait()
            return process_handle

        elif sys.platform == 'win32':
            process_handle = self.run_command_background(command)
            return process_handle

    def linux_trace_pid(self, command: str, num_processes_before: int):
        num_processes_after = len(trace_processes_for_cmd(command))
        if num_processes_before == num_processes_after:
            raise ComponentLaunchFailedError()

        process_handle = trace_pid(command)
        return process_handle

    def spawn_in_background(self, command):
        """for long-running processes / servers - on linux there is a process id
        tracing step because Popen returns a pid for a detached process (not the one we actually
        want)"""
        if sys.platform in ('linux', 'darwin'):
            num_processes_before = len(trace_processes_for_cmd(command))
            self.run_command_background(command)
            time.sleep(1)  # allow brief time window for process to fail at startup

            process_handle = self.linux_trace_pid(command, num_processes_before)
            return process_handle

        elif sys.platform == 'win32':
            process_handle = self.run_command_background(command)
            return process_handle

    def spawn_in_new_console(self, command):
        """for long-running processes / servers - on linux there is a process id tracing step
        because Popen returns a pid for a detached process (not the one we actually want)"""
        if sys.platform in ('linux', 'darwin'):
            num_processes_before = len(trace_processes_for_cmd(command))
            try:
                self.run_command_new_window(command)
            except ComponentLaunchFailedError:
                logger.error(f"failed to launch long-running process: {command}. On linux cloud "
                             f"servers try using the --background flag e.g. electrumsv-sdk start "
                             f"--background node.")
                raise
            time.sleep(1)  # allow brief time window for process to fail at startup

            process_handle = self.linux_trace_pid(command, num_processes_before)
            return process_handle

        elif sys.platform == 'win32':
            process_handle = self.run_command_new_window(command)
            return process_handle

    def import_plugin_component(self, component_name: ComponentName):
        component = importlib.import_module(f'.{component_name}',
                                            package='electrumsv_sdk.builtin_components')
        return component

    def configure_paths(self, component_name: ComponentName):
        repo = self.global_cli_flags[ComponentOptions.REPO]
        branch = self.global_cli_flags[ComponentOptions.BRANCH]
        component = self.import_plugin_component(component_name)
        if hasattr(component, 'configure_paths'):
            self.component_module.configure_paths(self, repo, branch)

    def kill_component(self):
        """generic, cross-platform way of killing components (by --id or <component_type>)"""
        id = self.global_cli_flags[ComponentOptions.ID]
        components_state = self.component_store.get_status()

        # stop all running components of: <component_type>
        if self.selected_stop_component:
            for component in components_state:
                if component.get("component_type") == self.selected_stop_component:
                    kill_process(component['pid'])
                    logger.info(f"terminated: {component.get('id')}")

        # stop component according to unique: --id
        if id:
            for component in components_state:
                if component.get("id") == id and \
                        component.get("component_state") == ComponentState.Running:
                    kill_process(component['pid'])
                    logger.info(f"terminated: {id}")

    def import_plugin_component_from_id(self, component_id: str):
        component_data = self.component_store.component_status_data_by_id(component_id)
        if component_data == {}:
            logger.error(f"no component data found for id: {component_id}")
            sys.exit(1)
        else:
            component_name = component_data['component_type']
            return self.import_plugin_component(component_name)
