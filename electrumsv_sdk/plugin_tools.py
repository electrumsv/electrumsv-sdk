import datetime
import logging
import os
import time
from pathlib import Path
import sys
from typing import Dict, Callable, Tuple, Set, List, Any, Optional
import requests

from .sdk_types import AbstractPlugin, SelectedComponent
from .constants import DATADIR, REMOTE_REPOS_DIR, LOGS_DIR, NETWORKS_LIST, PYTHON_LIB_DIR
from .components import ComponentStore, ComponentTypedDict, ComponentMetadata
from .utils import port_is_in_use, is_default_component_id, is_remote_repo, checkout_branch, \
    spawn_inline, spawn_new_terminal, spawn_background_supervised, prepend_to_pythonpath
from .config import Config


class PluginTools:
    """This contains methods that are common to all/many different plugins"""

    def __init__(self, plugin: AbstractPlugin, config: Config):
        self.plugin = plugin
        self.config = config
        self.component_store = ComponentStore()
        self.logger = logging.getLogger("plugin-tools")

    def allocate_port(self) -> int:
        assert self.plugin.id is not None  # typing bug
        component_port = self.get_component_port(self.plugin.DEFAULT_PORT,
            self.plugin.COMPONENT_NAME, self.plugin.id)
        return component_port

    def allocate_datadir_and_id(self) -> Tuple[Path, str]:
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

    def call_for_component_id_or_type(self, component_name: SelectedComponent,
            callable: Callable[[ComponentTypedDict], None]) -> None:
        """Used to either kill/stop/reset components by --id or <component_type>)
        - callable is called with one argument: component_dict with all relevant info about the
        component of interest - if there are many components of a particular type then the
        'callable' will be called multiple times.
        """
        id = self.config.component_id
        components_state = self.component_store.get_status(component_name)

        # stop component according to unique: --id
        if id:
            for component_dict in components_state.values():
                if component_dict.get("id") == id:
                    callable(component_dict)
                    self.logger.debug(f"terminated: {id}")

        # stop all running components of: <component_type>
        elif component_name:
            for component_dict in components_state.values():
                if component_dict.get("component_type") == component_name:
                    callable(component_dict)
                    self.logger.debug(f"terminated: {component_dict.get('id')}")

    def get_component_datadir(self, component_name: str) -> Tuple[Path, str]:
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
        reserved_ports: Set[int] = set()
        reserved_ports_list: List[int] = []
        for component_name in self.component_store.component_map:
            try:
                component_module = self.component_store.import_plugin_module(component_name)
                # avoids instantiation by accessing RESERVED_PORTS as a class attribute
                for port in component_module.Plugin.RESERVED_PORTS:
                    reserved_ports.add(port)
                    reserved_ports_list.append(port)

                if len(reserved_ports) != len(reserved_ports_list):
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

    def get_component_port(self, default_component_port: int, component_name: str,
            component_id: str) -> int:
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
            int=6, duration: float=1.0, timeout: float=0.5, http_method: str='get',
            payload: Optional[Dict[Any, Any]]=None, component_name: Optional[str]=None,
            verify_ssl: bool=False) -> bool:

        if not component_name and self.plugin.component_info:
            component_name = self.plugin.component_info.component_type
        elif not component_name and not self.plugin.component_info:
            raise Exception(f"Unknown component_name")

        for sleep_time in [duration] * retries:
            self.logger.debug(f"Polling {component_name}...")
            try:
                result = getattr(requests, http_method)(status_endpoint, timeout=timeout,
                    data=payload, verify=verify_ssl)
                result.raise_for_status()
                return True
            except Exception as e:
                pass

            time.sleep(sleep_time)
        return False

    def spawn_process(self, command: str, env_vars: Dict[str, str], id: str, component_name: str,
            src: Optional[Path]=None, logfile: Optional[Path]=None,
            status_endpoint: Optional[str]=None,
            metadata: Optional[ComponentMetadata]=None) -> None:

        if not env_vars:
            env_vars = {}

        assert isinstance(command, str)
        if self.config.background_flag:
            spawn_background_supervised(command, env_vars, id, component_name, src, logfile,
                status_endpoint, metadata)
        elif self.config.inline_flag:
            spawn_inline(command, env_vars, id, component_name, src, logfile,
                status_endpoint, metadata)
            sys.exit(0)
        elif self.config.new_terminal_flag:
            spawn_new_terminal(command, env_vars, id, component_name, src, logfile,
                status_endpoint, metadata)
        else:  # default
            spawn_new_terminal(command, env_vars, id, component_name, src, logfile,
                status_endpoint, metadata)

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

        else:
            return id

    def get_logfile_path(self, id: str) -> Path:
        """deterministic / standardised location for logging to file"""
        assert id is not None, "component id cannot be Null when deriving logfile path"
        dt = datetime.datetime.now()
        logfile_name = f"{dt.day}_{dt.month}_{dt.year}_{dt.hour}_{dt.minute}_{dt.second}.log"
        logpath = LOGS_DIR.joinpath(self.plugin.COMPONENT_NAME).joinpath(f"{id}")
        os.makedirs(logpath, exist_ok=True)
        logfile = logpath.joinpath(f"{logfile_name}")
        return logfile

    def set_network(self) -> None:
        # make sure that only one network is set on cli
        count_networks_selected = len([self.config.cli_extension_args[network] for network in
            NETWORKS_LIST if self.config.cli_extension_args[network] is True])
        if count_networks_selected > 1:
            self.logger.error("you must only select a single network")
            sys.exit(1)

        if count_networks_selected == 0:
            self.plugin.network = self.plugin.network
        if count_networks_selected == 1:
            for network in NETWORKS_LIST:
                if self.config.cli_extension_args[network]:
                    self.plugin.network = network

    def modify_pythonpath_for_portability(self, component_source_dir: Optional[Path]) -> None:
        """This is only necessary as a workaround to get the SDK working with a portable / bundled
        version of python"""
        additions = []
        if component_source_dir:
            additions = [Path(component_source_dir)]
        additions += [
            PYTHON_LIB_DIR / self.plugin.COMPONENT_NAME,
            REMOTE_REPOS_DIR,
        ]
        prepend_to_pythonpath(additions)
