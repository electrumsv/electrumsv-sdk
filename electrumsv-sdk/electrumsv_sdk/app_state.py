import argparse
from importlib import import_module
import json
import logging
import os
import subprocess
import time
from pathlib import Path
import shutil
import stat
import sys
from types import ModuleType
from typing import Dict, List, Optional, Callable

import requests
from electrumsv_node import electrumsv_node

from .utils import trace_processes_for_cmd, trace_pid, make_bat_file, make_bash_file
from .constants import ComponentLaunchFailedError
from .argparsing import ArgParser
from .components import ComponentOptions, ComponentStore, Component
from .controller import Controller
from .handlers import Handlers

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger("status")
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)
orm_logger = logging.getLogger("peewee")
orm_logger.setLevel(logging.WARNING)


class AppState:
    """Only electrumsv paths are saved to config.json so that 'reset' works on correct wallet."""

    def __init__(self):
        datadir = None
        if sys.platform == "win32":
            datadir = Path(os.environ.get("LOCALAPPDATA")) / "ElectrumSV-SDK"
        if datadir is None:
            datadir = Path.home() / ".electrumsv-sdk"

        # set main application paths
        self.sdk_home_dir = datadir
        self.remote_repos_dir = self.sdk_home_dir.joinpath("remote_repos")
        self.shell_scripts_dir = self.sdk_home_dir.joinpath("shell_scripts")
        self.datadir = self.sdk_home_dir.joinpath("component_datadirs")
        sys.path.append(f"{self.sdk_home_dir}")
        self.logs_dir = self.sdk_home_dir.joinpath("logs")
        self.config_path = self.sdk_home_dir.joinpath("config.json")
        os.makedirs(self.remote_repos_dir, exist_ok=True)
        os.makedirs(self.shell_scripts_dir, exist_ok=True)
        os.makedirs(self.datadir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

        self.sdk_package_dir = Path(MODULE_DIR)

        # plugins
        self.builtin_components_dir = Path(MODULE_DIR).joinpath("builtin_components")
        self.user_plugins_dir = self.sdk_home_dir.joinpath("user_plugins")
        self.local_plugins_dir = Path(os.getcwd()).joinpath("electrumsv_sdk_plugins")
        os.makedirs(self.user_plugins_dir, exist_ok=True)

        self.component_map = self.get_component_map()

        self.component_store = ComponentStore(self)
        self.arparser = ArgParser(self)
        self.controller = Controller(self)
        self.handlers = Handlers(self)

        self.component_module = None  # e.g. builtin_components.node.node.py module
        self.component_info: Optional[Component] = None  # dict conversion <-> status_monitor

        if sys.platform in ['linux', 'darwin']:
            self.linux_venv_dir = self.sdk_home_dir.joinpath("sdk_venv")
            self.python = self.linux_venv_dir.joinpath("bin").joinpath("python")
            self.run_command_current_shell(
                f"{sys.executable} -m venv {self.linux_venv_dir}")
        else:
            self.python = sys.executable

        # namespaces and argparsing
        self.NAMESPACE = ""  # 'start', 'stop', 'reset', 'node', or 'status'
        self.parser_map: Dict[str, argparse.ArgumentParser] = {}  # namespace: ArgumentParser
        self.parser_raw_args_map: Dict[str, List[str]] = {}  # {namespace: raw arguments}
        self.parser_parsed_args_map = {}  # {namespace: parsed arguments}
        self.component_args = []  # e.g. store arguments to pass to the electrumsv's cli interface

        # status_monitor special-case component type
        self.status_monitor_dir = self.sdk_package_dir.joinpath("status_server")
        self.status_monitor_logging_path = self.logs_dir.joinpath("status_monitor")
        os.makedirs(self.status_monitor_logging_path, exist_ok=True)

        self.selected_component: Optional[str] = None

        self.global_cli_flags: Dict[str] = {}
        self.node_args = None

        self.global_cli_flags[ComponentOptions.NEW] = False
        self.global_cli_flags[ComponentOptions.GUI] = False
        self.global_cli_flags[ComponentOptions.BACKGROUND] = False
        self.global_cli_flags[ComponentOptions.ID] = ""
        self.global_cli_flags[ComponentOptions.REPO] = ""
        self.global_cli_flags[ComponentOptions.BRANCH] = ""

    def get_component_map(self):
        component_map = {}  # component_name: <component_dir>
        ignored = {'__init__.py', '__pycache__', '.idea', '.vscode'}

        # Layer 1
        builtin_components_list = [
            component_type for component_type
            in os.listdir(self.builtin_components_dir)
            if component_type not in ignored
        ]
        for component_type in builtin_components_list:
            component_map[component_type] = self.builtin_components_dir

        # Layer 2 - overrides builtins (if there is a name clash)
        user_plugins_list = [
            component_type for component_type
            in os.listdir(self.user_plugins_dir)
            if component_type not in ignored
        ]
        for component_type in user_plugins_list:
            component_map[component_type] = self.user_plugins_dir

        # Layer 3 - overrides both builtin & user_plugins_list (if there is a name clash)
        if self.local_plugins_dir.exists():
            local_components_list = [
                component_type for component_type
                in os.listdir(self.local_plugins_dir)
                if component_type not in ignored
            ]
            for component_type in local_components_list:
                component_map[component_type] = self.local_plugins_dir

        return component_map

    def get_id(self, component_name: str):
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
        sdk_datadir = Path.home() / ".electrumsv-sdk"
        linux_venv_dir = sdk_datadir.joinpath("sdk_venv")
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

    def is_component_running_http(self, status_endpoint: str, retries:
            int=6, duration: float=1.0, timeout: float=0.5, http_method='get',
            payload: Dict=None, component_name: str=None, verify_ssl=False) -> bool:

        if not component_name and self.component_info:
            component_name = self.component_info.component_type
        elif not component_name and not self.component_info:
            raise Exception(f"Unknown component_name")

        for sleep_time in [duration] * retries:
            logger.debug(f"Polling {component_name}...")
            try:
                result = getattr(requests, http_method)(status_endpoint, timeout=timeout,
                    data=payload, verify=False)
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

    def import_plugin_component(self, component_name: str) -> Optional[ModuleType]:
        plugin_dir = self.component_map.get(component_name)
        if not plugin_dir:
            logger.error(f"plugin for {component_name} not found")
            sys.exit(1)
        basename = os.path.basename(plugin_dir)
        logger.debug(f"loading plugin module '{component_name}' from: {plugin_dir}")
        if basename == 'builtin_components':
            # do relative import
            component_module = import_module(f'.{basename}.{component_name}',
                package="electrumsv_sdk")

        elif basename == 'user_plugins':
            # do absolute import (sdk_home_dir was added to sys.path to make this work)
            component_module = import_module(f'{basename}.{component_name}')

        elif basename == 'electrumsv_sdk_plugins':
            # do absolute import
            component_module = import_module(f'{basename}.{component_name}')

        return component_module

    def configure_paths(self, component_name: str):
        repo = self.global_cli_flags[ComponentOptions.REPO]
        branch = self.global_cli_flags[ComponentOptions.BRANCH]
        component = self.import_plugin_component(component_name)
        if hasattr(component, 'configure_paths'):
            self.component_module.configure_paths(self, repo, branch)

    def call_for_component_id_or_type(self, component_name: str, callable: Callable):
        """Used to either kill/stop/reset components by --id or <component_type>)
        - callable is called with one argument: component_dict with all relevant info about the
        component of interest - if there are many components of a particular type then the
        'callable' will be called multiple times.
        """
        id = self.global_cli_flags[ComponentOptions.ID]
        components_state = self.component_store.get_status()

        # stop all running components of: <component_type>
        if self.selected_component:
            for component_dict in components_state.values():
                if component_dict.get("component_type") == component_name:
                    callable(component_dict)
                    logger.info(f"terminated: {component_dict.get('id')}")

        # stop component according to unique: --id
        if id:
            for component_dict in components_state.values():
                if component_dict.get("id") == id:
                    callable(component_dict)
                    logger.info(f"terminated: {id}")

    def import_plugin_component_from_id(self, component_id: str):
        component_data = self.component_store.component_status_data_by_id(component_id)
        if component_data == {}:
            logger.error(f"no component data found for id: {component_id}")
            sys.exit(1)
        else:
            component_name = component_data['component_type']
            return self.import_plugin_component(component_name)

    def make_shell_script_for_component(self, list_of_shell_commands: List[str],
            component_name: str):

        if sys.platform == "win32":
            make_bat_file(component_name + ".bat", list_of_shell_commands)

        elif sys.platform in ["linux", "darwin"]:
            make_bash_file(component_name + ".sh", list_of_shell_commands)

    def get_component_datadir(self, component_name: str):
        # Todo - use this generically for node and electrumsv
        """to run multiple instances of a component requires multiple data directories"""
        def is_new_and_no_id(id, new) -> bool:
            return id == "" and new
        def is_new_and_id(id, new) -> bool:
            return id != "" and new
        def is_not_new_and_no_id(id, new) -> bool:
            return id == "" and not new
        def is_not_new_and_id(id, new) -> bool:
            return id != "" and not new

        new = self.global_cli_flags[ComponentOptions.NEW]
        id = self.global_cli_flags[ComponentOptions.ID]

        # autoincrement <component_name>1 -> <component_name>2 etc. new datadir is found
        if is_new_and_no_id(id, new):
            count = 1
            while True:
                self.global_cli_flags[ComponentOptions.ID] = id = \
                    str(component_name) + str(count)
                new_dir = self.datadir.joinpath(f"{component_name}/{id}")
                if not new_dir.exists():
                    break
                else:
                    count += 1
            logger.debug(f"Using new user-specified data dir ({id})")

        elif is_new_and_id(id, new):
            new_dir = self.datadir.joinpath(f"{component_name}/{id}")
            if new_dir.exists():
                logger.debug(f"User-specified data directory: {new_dir} already exists ("
                      f"either drop the --new flag or choose a unique identifier).")
                sys.exit(1)
            logger.debug(f"Using user-specified data dir ({new_dir})")

        elif is_not_new_and_id(id, new):
            new_dir = self.datadir.joinpath(f"{component_name}/{id}")
            if not new_dir.exists():
                logger.debug(f"User-specified data directory: {new_dir} does not exist"
                             f" and so will be created anew.")
            logger.debug(f"Using user-specified data dir ({new_dir})")

        elif is_not_new_and_no_id(id, new):
            id = self.get_id(component_name)  # default
            new_dir = self.datadir.joinpath(f"{component_name}/{id}")
            logger.debug(f"Using default data dir ({new_dir})")

        logger.debug(f"data dir = {new_dir}")
        return new_dir
