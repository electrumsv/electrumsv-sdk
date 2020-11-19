import logging
import os
import subprocess
import time
from pathlib import Path
import sys
from typing import Dict, List, Optional, Callable, Union, Tuple
import psutil
import requests

from .abstract_plugin import AbstractPlugin
from .utils import trace_processes_for_cmd, trace_pid, make_bat_file, make_bash_file, \
    port_is_in_use, is_default_component_id, is_remote_repo, checkout_branch
from .constants import ComponentLaunchFailedError, SHELL_SCRIPTS_DIR, DATADIR, REMOTE_REPOS_DIR
from .components import ComponentStore
from .config import ImmutableConfig


class PluginTools:
    """This contains methods that are common to all/many different plugins"""

    def __init__(self, plugin: AbstractPlugin, config: ImmutableConfig):
        self.plugin = plugin
        self.config = config
        self.component_store = ComponentStore()
        self.logger = logging.getLogger("plugin-tools")

    def allocate_port(self):
        assert self.plugin.id is not None
        component_port = self.get_component_port(self.plugin.DEFAULT_PORT,
            self.plugin.COMPONENT_NAME, self.plugin.id)
        return component_port

    def allocate_datadir_and_id(self):
        component_datadir, component_id = \
            self.get_component_datadir(self.plugin.COMPONENT_NAME)
        return component_datadir, component_id

    def get_source_dir(self, dirname: str) -> Path:
        if is_remote_repo(self.config.repo):
            self.plugin.src = REMOTE_REPOS_DIR.joinpath(dirname)
            self.logger.debug(f"Remote repo installation directory for: "
                              f"{self.plugin.COMPONENT_NAME}: "f"{self.plugin.src}")
        else:
            self.logger.debug(f"Targetting local repo {self.plugin.COMPONENT_NAME} at: "
                         f"{self.config.repo}")
            assert Path(self.config.repo).exists(), f"the path {self.config.repo} does not exist!"
            if self.config.branch != "":
                checkout_branch(self.config.branch)
            self.plugin.src = Path(self.config.repo)
        return self.plugin.src

    def call_for_component_id_or_type(self, component_name: str, callable: Callable):
        """Used to either kill/stop/reset components by --id or <component_type>)
        - callable is called with one argument: component_dict with all relevant info about the
        component of interest - if there are many components of a particular type then the
        'callable' will be called multiple times.
        """
        id = self.config.component_id
        components_state = self.component_store.get_status()

        # stop component according to unique: --id
        if id:
            for component_dict in components_state.values():
                if component_dict.get("id") == id:
                    callable(component_dict)
                    self.logger.info(f"terminated: {id}")

        # stop all running components of: <component_type>
        elif component_name:
            for component_dict in components_state.values():
                if component_dict.get("component_type") == component_name:
                    callable(component_dict)
                    self.logger.info(f"terminated: {component_dict.get('id')}")

    def make_shell_script_for_component(self, list_of_shell_commands: List[str],
            component_name: str):
        os.makedirs(SHELL_SCRIPTS_DIR, exist_ok=True)
        os.chdir(SHELL_SCRIPTS_DIR)

        if sys.platform == "win32":
            make_bat_file(component_name + ".bat", list_of_shell_commands)

        elif sys.platform in ["linux", "darwin"]:
            make_bash_file(component_name + ".sh", list_of_shell_commands)

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

        new = self.config.new_flag
        id = self.config.component_id

        # autoincrement <component_name>1 -> <component_name>2 etc. new DATADIR is found
        if is_new_and_no_id(id, new):
            count = 1
            while True:
                id = str(component_name) + str(count)
                new_dir = DATADIR.joinpath(f"{component_name}/{id}")
                if not new_dir.exists():
                    break
                else:
                    count += 1
            self.logger.debug(f"Using new user-specified data dir ({id})")

        elif is_new_and_id(id, new):
            new_dir = DATADIR.joinpath(f"{component_name}/{id}")
            if new_dir.exists():
                self.logger.debug(f"User-specified data directory: {new_dir} already exists ("
                      f"either drop the --new flag or choose a unique identifier).")
                sys.exit(1)
            self.logger.debug(f"Using user-specified data dir ({new_dir})")

        elif is_not_new_and_id(id, new):
            new_dir = DATADIR.joinpath(f"{component_name}/{id}")
            if not new_dir.exists():
                self.logger.debug(f"User-specified data directory: {new_dir} does not exist"
                             f" and so will be created anew.")
            self.logger.debug(f"Using user-specified data dir ({new_dir})")

        elif is_not_new_and_no_id(id, new):
            id = self.get_default_id(component_name)  # default
            new_dir = DATADIR.joinpath(f"{component_name}/{id}")
            self.logger.debug(f"Using default data dir ({new_dir})")

        os.makedirs(new_dir, exist_ok=True)
        self.logger.debug(f"data dir = {new_dir}")
        return new_dir, id

    def port_clash_check_ok(self) -> bool:
        reserved_ports = set()
        for component_name in self.component_store.component_map:
            try:
                component_module = self.component_store.import_plugin_module(component_name)
                component_module.Plugin: AbstractPlugin
                # avoids instantiation by accessing RESERVED_PORTS as a class attribute
                if component_module.Plugin.RESERVED_PORTS in reserved_ports:
                    self.logger.exception(
                        f"There is a conflict of reserved ports for component_module: "
                        f"{component_module} on ports: {component_module.Plugin.RESERVED_PORTS}. "
                        f"Please choose default ports for the plugin that do not clash.")
                    return False
            except AttributeError:
                self.logger.error(f"plugin: {component_name} does not have a Plugin class with "
                    f"the 'RESERVED_PORTS' class attribute - therefore the port clash check has "
                    f"been skipped")
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

    def is_component_running_http(self, status_endpoint: str, retries:
            int=6, duration: float=1.0, timeout: float=0.5, http_method='get',
            payload: Dict=None, component_name: str=None, verify_ssl=False) -> bool:

        if not component_name and self.plugin.component_info:
            component_name = self.plugin.component_info.component_type
        elif not component_name and not self.plugin.component_info:
            raise Exception(f"Unknown component_name")

        for sleep_time in [duration] * retries:
            self.logger.debug(f"Polling {component_name}...")
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
            script = SHELL_SCRIPTS_DIR.joinpath(f"{script_name}.bat")
        elif sys.platform in ("linux", "darwin"):
            script = SHELL_SCRIPTS_DIR.joinpath(f"{script_name}.sh")
        else:
            self.logger.error(f"unsupported platform: {sys.platform}")
            raise NotImplementedError
        return str(script)

    def spawn_process(self, command: str) -> subprocess.Popen:
        assert isinstance(command, str)
        if self.config.background_flag:
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
            self.logger.info(
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
                self.logger.error(
                    f"failed to launch long-running process: {command}. On linux cloud "
                    f"servers try using the --background flag e.g. electrumsv-sdk start "
                    f"--background node.")
                raise
            time.sleep(1)  # allow brief time window for process to fail at startup

            process_handle = self.linux_trace_pid(command, num_processes_before)
            return process_handle

        elif sys.platform == 'win32':
            process_handle = self.run_command_new_window(command)
            return process_handle

    def get_default_id(self, component_name: str) -> str:
        return component_name + str(1)

    def get_id(self, component_name: str) -> str:
        """This method is exclusively for single-instance components.
        Multi-instance components (that use the --new flag) need to get allocated a component_id
        via the 'get_component_datadir()' method"""
        id = self.config.component_id
        new = self.config.new_flag
        if not id and not new:  # Default component id (and port + DATADIR)
            return self.get_default_id(component_name)

        elif id:
            return id

        elif new:
            self.logger.error("The --new flag is only for multi-instance conponents")
