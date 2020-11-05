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
from typing import Dict, List, Optional, Callable, Union, Any, Tuple

import psutil
import requests
from electrumsv_node import electrumsv_node

from .utils import trace_processes_for_cmd, trace_pid, make_bat_file, make_bash_file, \
    port_is_in_use, is_default_component_id
from .constants import ComponentLaunchFailedError, LOCAL_PLUGINS_DIRNAME
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
        self.sdk_home_dir: Path = datadir
        self.remote_repos_dir: Path = self.sdk_home_dir.joinpath("remote_repos")
        self.shell_scripts_dir: Path = self.sdk_home_dir.joinpath("shell_scripts")
        self.datadir: Path = self.sdk_home_dir.joinpath("component_datadirs")
        sys.path.append(f"{self.sdk_home_dir}")
        self.logs_dir: Path = self.sdk_home_dir.joinpath("logs")
        self.config_path: Path = self.sdk_home_dir.joinpath("config.json")
        os.makedirs(self.remote_repos_dir, exist_ok=True)
        os.makedirs(self.shell_scripts_dir, exist_ok=True)
        os.makedirs(self.datadir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        self.calling_context_dir: Path = Path(os.getcwd())

        self.sdk_package_dir: Path = Path(MODULE_DIR)

        # plugins
        self.builtin_components_dir: Path = Path(MODULE_DIR).joinpath("builtin_components")
        self.user_plugins_dir: Path = self.sdk_home_dir.joinpath("user_plugins")
        self.local_plugins_dir: Path = Path(os.getcwd()).joinpath("electrumsv_sdk_plugins")
        self.add_local_plugin_to_sys_path()
        sys.path.append(str(MODULE_DIR))  # for dynamic import of builtin_components
        os.makedirs(self.user_plugins_dir, exist_ok=True)

        self.component_map: Dict[str, Path] = self.get_component_map()

        self.component_store: ComponentStore = ComponentStore(self)
        self.arparser: ArgParser = ArgParser(self)
        self.controller: Controller = Controller(self)
        self.handlers: Handlers = Handlers(self)

        self.component_module: Optional[ModuleType] = None  # e.g. builtin_components.node
        self.component_info: Optional[Component] = None  # dict conversion <-> status_monitor
        self.python = sys.executable

        # namespaces and argparsing
        self.NAMESPACE = ""  # 'start', 'stop', 'reset', 'node', or 'status'
        self.parser_map: Dict[str, argparse.ArgumentParser] = {}  # namespace: ArgumentParser
        self.parser_raw_args_map: Dict[str, List[str]] = {}  # {namespace: raw arguments}
        self.parser_parsed_args_map = {}  # {namespace: parsed arguments}
        self.component_args = []  # e.g. store arguments to pass to the electrumsv's cli interface

        # Todo - these globals should not be mutated (and merely reflect whatever commandline
        #  configuration was set at the beginning).
        #  This is not yet adhered to fully but we should work towards it possibly with a
        #  Configuration object that is instantiated and passed around inside of the plugins
        #  - AustEcon
        self.selected_component: Optional[str] = None

        self.global_cli_flags: Dict[str, Any] = {}
        self.node_args = None
        self.global_cli_flags[ComponentOptions.NEW] = False
        self.global_cli_flags[ComponentOptions.GUI] = False
        self.global_cli_flags[ComponentOptions.BACKGROUND] = False
        self.global_cli_flags[ComponentOptions.ID] = ""
        self.global_cli_flags[ComponentOptions.REPO] = ""
        self.global_cli_flags[ComponentOptions.BRANCH] = ""
        self.component_datadir = None

    def get_component_map(self) -> Dict[str, Path]:
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

    def get_default_id(self, component_name: str) -> str:
        return component_name + str(1)

    def get_id(self, component_name: str) -> str:
        """This method is exclusively for single-instance components.
        Multi-instance components (that use the --new flag) need to get allocated a component_id
        via the 'get_component_datadir()' method"""
        id = self.global_cli_flags[ComponentOptions.ID]
        new = self.global_cli_flags[ComponentOptions.NEW]
        if not id and not new:  # Default component id (and port + datadir)
            id = self.get_default_id(component_name)
            return id

        elif id:
            return id

        elif new:
            logger.error("The --new flag is only for multi-instance conponents")

    def save_repo_paths(self) -> None:
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

    def purge_prev_installs_if_exist(self) -> None:
        def remove_readonly(func, path, excinfo):  # .git is read-only
            os.chmod(path, stat.S_IWRITE)
            func(path)

        if self.remote_repos_dir.exists():
            shutil.rmtree(self.remote_repos_dir, onerror=remove_readonly)
            os.makedirs(self.remote_repos_dir, exist_ok=True)
        if self.shell_scripts_dir.exists():
            shutil.rmtree(self.shell_scripts_dir, onerror=remove_readonly)
            os.makedirs(self.shell_scripts_dir, exist_ok=True)

    def setup_python_venv(self) -> None:
        sdk_requirements_path = Path(MODULE_DIR).parent.joinpath("requirements")\
            .joinpath("requirements.txt")
        sdk_requirements_linux_path = Path(MODULE_DIR).parent.joinpath("requirements").joinpath(
            "requirements-linux.txt")
        subprocess.run(f"{self.python} -m pip install --user -r {sdk_requirements_path}",
                       shell=True, check=True)
        subprocess.run(f"{self.python} -m pip install --user -r {sdk_requirements_linux_path}",
                       shell=True, check=True)

    def handle_first_ever_run(self) -> None:
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

    def derive_shell_script_path(self, component_name: str) -> str:
        script_name = component_name

        if sys.platform == "win32":
            script = self.shell_scripts_dir.joinpath(f"{script_name}.bat")
        elif sys.platform in ("linux", "darwin"):
            script = self.shell_scripts_dir.joinpath(f"{script_name}.sh")
        else:
            logger.error(f"unsupported platform: {sys.platform}")
            raise NotImplementedError
        return str(script)

    def spawn_process(self, command: str) -> subprocess.Popen:
        assert isinstance(command, str)
        if self.global_cli_flags[ComponentOptions.BACKGROUND]:
            return self.spawn_in_background(command)
        else:
            return self.spawn_in_new_console(command)

    def run_command_current_shell(self, command: str):
        return subprocess.run(command, shell=True, check=True)

    def run_command_background(self, command: str) -> subprocess.Popen:
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

    def run_command_new_window(self, command: str) -> subprocess.Popen:
        if sys.platform in ('linux', 'darwin'):
            # todo gnome-terminal part will not work cross-platform for spawning new terminals
            process_handle = subprocess.Popen(f"gnome-terminal -- {command}", shell=True,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process_handle.wait()
            return process_handle

        elif sys.platform == 'win32':
            process_handle = self.run_command_background(command)
            return process_handle

    def linux_trace_pid(self, command: str, num_processes_before: int) -> psutil.Process:
        num_processes_after = len(trace_processes_for_cmd(command))
        if num_processes_before == num_processes_after:
            raise ComponentLaunchFailedError()

        process_handle = trace_pid(command)
        return process_handle

    def spawn_in_background(self, command: str) -> Union[subprocess.Popen, psutil.Process]:
        """for long-running processes / servers - on linux there is a process id
        tracing step because Popen returns a pid for a detached process (not the one we actually
        want)"""
        assert isinstance(command, str)
        if sys.platform in ('linux', 'darwin'):
            num_processes_before = len(trace_processes_for_cmd(command))
            self.run_command_background(command)
            time.sleep(1)  # allow brief time window for process to fail at startup

            process_handle = self.linux_trace_pid(command, num_processes_before)
            return process_handle

        elif sys.platform == 'win32':
            process_handle = self.run_command_background(command)
            return process_handle

    def spawn_in_new_console(self, command: str) -> Union[subprocess.Popen, psutil.Process]:
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
        # logger.debug(f"loading plugin module '{component_name}' from: {plugin_dir}")
        if basename == 'builtin_components':
            # do relative import
            component_module = import_module(f'.{basename}.{component_name}',
                package="electrumsv_sdk")

        elif basename == 'user_plugins':
            # do absolute import (sdk_home_dir was added to sys.path to make this work)
            component_module = import_module(f'{basename}.{component_name}')

        elif basename == LOCAL_PLUGINS_DIRNAME:
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

        # stop component according to unique: --id
        if id:
            for component_dict in components_state.values():
                if component_dict.get("id") == id:
                    callable(component_dict)
                    logger.info(f"terminated: {id}")

        # stop all running components of: <component_type>
        elif component_name:
            for component_dict in components_state.values():
                if component_dict.get("component_type") == component_name:
                    callable(component_dict)
                    logger.info(f"terminated: {component_dict.get('id')}")

    def make_shell_script_for_component(self, list_of_shell_commands: List[str],
            component_name: str):
        os.makedirs(self.shell_scripts_dir, exist_ok=True)
        os.chdir(self.shell_scripts_dir)

        if sys.platform == "win32":
            make_bat_file(component_name + ".bat", list_of_shell_commands)

        elif sys.platform in ["linux", "darwin"]:
            make_bash_file(component_name + ".sh", list_of_shell_commands)

    def add_local_plugin_to_sys_path(self):
        """the parent dir of the 'electrumsv_sdk_plugins' dir needs to be on sys.path to be
        locatable for dynamic importing."""
        sys.path.append(f"{self.calling_context_dir}")

    def get_component_datadir(self, component_name: str) -> Tuple[Path, Optional[str]]:
        """Used for multi-instance components"""
        def is_new_and_no_id(id: str, new: bool) -> bool:
            return id == "" and new
        def is_new_and_id(id: str, new: bool) -> bool:
            return id != "" and new
        def is_not_new_and_no_id(id: str, new: bool) -> bool:
            return id == "" and not new
        def is_not_new_and_id(id: str, new: bool) -> bool:
            return id != "" and not new

        new = self.global_cli_flags[ComponentOptions.NEW]
        id = self.global_cli_flags[ComponentOptions.ID]

        # autoincrement <component_name>1 -> <component_name>2 etc. new datadir is found
        if is_new_and_no_id(id, new):
            count = 1
            while True:
                id = str(component_name) + str(count)
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
            id = self.get_default_id(component_name)  # default
            new_dir = self.datadir.joinpath(f"{component_name}/{id}")
            logger.debug(f"Using default data dir ({new_dir})")

        os.makedirs(new_dir, exist_ok=True)
        logger.debug(f"data dir = {new_dir}")
        return new_dir, id

    def port_clash_check_ok(self) -> bool:
        reserved_ports = set()
        for component_name in self.component_map:
            component_module = self.import_plugin_component(component_name)
            if component_module.RESERVED_PORTS in reserved_ports:
                logger.exception(f"There is a conflict of reserved ports for component_module: "
                                 f"{component_module} on ports: {component_module.RESERVED_PORTS}. "
                                 f"Please choose default ports for the plugin that do not clash.")
                return False
        return True

    def get_component_port(self, default_component_port, component_name, component_id) -> int:
        """ensure that no other plugin uses any of the default ports as they are strictly
        reserved for the default component ids."""
        if not self.port_clash_check_ok():
            return sys.exit(1)

        # reserved ports
        if is_default_component_id(component_name, component_id):
            assert not port_is_in_use(default_component_port), \
                f"an unknown application is using this port: {default_component_port}"
            return default_component_port

        # a non-default component id -> unreserved + unused ports only
        port = default_component_port + 10
        while True:
            if port_is_in_use(port):
                port += 10
            else:
                break
        return port
