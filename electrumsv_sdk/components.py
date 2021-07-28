"""
all status changes for each component are persisted and read from component_state.json

STARTUP:
- immediate success is achieved (no exceptions at launch)    state=Running
- immediate failure occurs at launch                         state=Failed

SHUTDOWN
- on shutdown of an 'SDK component'                          state=Stopped

STATUS-MONITOR (server)
- pings SDK builtin_components periodically to see if they
are still online

- if state=Running & reachable then                          state=Running
- if state=Running & NOT reachable then                      state=Failed
- if state=Stopped & reachable then                          BUG (should not happen)
- if state=Stopped & NOT reachable then                      state=Stopped
- if state=Failed & reachable then                           state=Running
- if state=Failed & NOT reachable then remains as            state=Failed

the status-monitor server will continue monitoring all entries in the component_state.json
regardless of which state they are in.
- If state=Failed but the service becomes reachable subsequently, the status will return to
state=Running.

- terminated builtin_components without using the SDK interface      state=Failed
"""
import datetime
import json
import logging
import os
import sys
from importlib import import_module
from pathlib import Path
from typing import Optional, Union, Dict, cast
from filelock import FileLock

from .config import Config
from .sdk_types import AbstractPlugin, AbstractModuleType
from .constants import SDK_HOME_DIR, LOCAL_PLUGINS_DIR, USER_PLUGINS_DIR, BUILTIN_COMPONENTS_DIR, \
    LOCAL_PLUGINS_DIRNAME, ComponentState, BUILTIN_PLUGINS_DIRNAME, USER_PLUGINS_DIRNAME

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger("component-store")


def get_str_datetime() -> str:
    return datetime.datetime.now().strftime(TIME_FORMAT)


from typing import TypedDict


class ComponentMetadata(TypedDict, total=False):
    rpcport: int
    rpchost: str
    datadir: str
    p2p_port: int
    config_path: str  # path for electrumsv wallets (depending on which network)


class ComponentTypedDict(TypedDict):
    id: str
    pid: Optional[int]
    component_type: str
    location: Union[str, Path]
    status_endpoint: Optional[str]
    component_state: Optional[str]
    metadata: Optional[ComponentMetadata]
    logging_path: Optional[Union[str, Path]]
    last_updated: Optional[str]


class Component:
    def __init__(
        self,
        id: str,
        pid: Optional[int],
        component_type: str,
        location: Union[str, Path],
        status_endpoint: Optional[str],
        component_state: Optional[str]=None,
        metadata: Optional[ComponentMetadata]=None,
        logging_path: Optional[Union[str, Path]]=None,
        last_updated: Optional[str]=None
    ):
        self.id = id  # human-readable identifier for instance
        self.pid = pid
        self.component_type = str(component_type)
        self.status_endpoint = status_endpoint
        self.component_state = ComponentState.from_str(str(component_state))
        self.location = str(location)
        self.metadata = metadata
        self.logging_path = str(logging_path)
        self.last_updated = last_updated
        if not last_updated:
            self.last_updated = get_str_datetime()

    def __repr__(self) -> str:
        return (
            f"Component(id={self.id}, pid={self.pid}, "
            f"component_type={self.component_type}, "
            f"status_endpoint={self.status_endpoint}, "
            f"component_state={self.component_state}, "
            f"location={self.location}, metadata={self.metadata}, "
            f"logging_path={self.logging_path}, "
            f"last_updated={self.last_updated})"
        )

    def to_dict(self) -> ComponentTypedDict:
        config_dict = ComponentTypedDict(
            id=self.id,
            pid=self.pid,
            component_type=self.component_type,
            location=self.location,
            status_endpoint=self.status_endpoint,
            component_state=self.component_state,
            metadata=self.metadata,
            logging_path=self.logging_path,
            last_updated=self.last_updated
        )
        return config_dict

    @classmethod
    def from_dict(cls, component_dict: ComponentTypedDict) -> "Component":
        component_dict['last_updated'] = get_str_datetime()
        return cls(**component_dict)


class ComponentStore:
    """multiprocess safe read/write access to component_state.json
    (which is basically acting as a stand-in for a database - which would be major overkill)"""

    def __init__(self) -> None:
        self.file_name = "component_state.json"
        self.lock_path = SDK_HOME_DIR / "component_state.json.lock"
        self.file_lock = FileLock(str(self.lock_path), timeout=5)
        self.component_state_path = SDK_HOME_DIR / self.file_name
        if not self.component_state_path.exists():
            open(self.component_state_path, 'w').close()
        self.component_map = self.get_component_map()

    def get_status(self, component_type: Optional[str]=None,
            component_id: Optional[str]=None) -> Dict[str, ComponentTypedDict]:
        filelock_logger = logging.getLogger("filelock")
        filelock_logger.setLevel(logging.WARNING)

        with self.file_lock:
            if self.component_state_path.exists():
                with open(self.component_state_path, "r") as f:
                    data = f.read()
                    component_state: Dict[str, ComponentTypedDict]
                    if data:
                        component_state = json.loads(data)
                    else:
                        component_state = {}

                if component_type and component_id:
                    raise ValueError("Cannot handle both 'component_type' and 'component_id'. "
                        "Please choose one or the other.")

                if component_type:
                    filtered_result: Dict[str, ComponentTypedDict] = {}
                    # Only save / modify the relevant component types
                    for key, val in component_state.items():
                        if val['component_type'] == component_type:
                            filtered_result[key] = val

                    return filtered_result

                if component_id:
                    result = component_state.get(component_id)
                    if result:
                        return {component_id: result}
                    raise ValueError(f"Component id: '{component_id}' not found in store.")

                return component_state
            else:
                return {}

    def update_status_file(self, new_component_info: Component) -> None:
        """updates to the *file* (component.json) - does *not* update the server"""

        component_state = {}
        with self.file_lock:
            if self.component_state_path.exists():
                with open(self.component_state_path, "r") as f:
                    data = f.read()
                    if data:
                        component_state = json.loads(data)
                    else:
                        component_state = {}
        assert isinstance(component_state, dict)
        component_state[new_component_info.id] = new_component_info.to_dict()

        with open(self.component_state_path, "w") as f:
            f.write(json.dumps(component_state, indent=4))
            f.flush()
        logger.debug(f"updated status: {new_component_info}")

    def component_status_data_by_id(self, component_id: str) -> Optional[ComponentTypedDict]:
        component_state = self.get_status()
        component_info = component_state.get(component_id)
        if component_info:
            return ComponentTypedDict(
                id=component_info['id'],
                pid=component_info['pid'],
                component_type=component_info['component_type'],
                location=component_info['location'],
                status_endpoint=component_info['status_endpoint'],
                component_state=component_info['component_state'],
                metadata=component_info['metadata'],
                logging_path=component_info['logging_path'],
                last_updated=component_info['last_updated']
            )

        logger.error("component id not found")
        return None

    def get_component_map(self) -> Dict[str, Path]:
        component_map = {}  # component_name: <component_dir>
        ignored = {'__init__.py', '__pycache__', '.idea', '.vscode'}

        # Layer 1
        builtin_components_list = [
            component_type for component_type
            in os.listdir(BUILTIN_COMPONENTS_DIR)
            if component_type not in ignored
        ]
        for component_type in builtin_components_list:
            component_map[component_type] = BUILTIN_COMPONENTS_DIR

        # Layer 2 - overrides builtins (if there is a name clash)
        user_plugins_list = [
            component_type for component_type
            in os.listdir(USER_PLUGINS_DIR)
            if component_type not in ignored
        ]
        for component_type in user_plugins_list:
            component_map[component_type] = USER_PLUGINS_DIR

        # Layer 3 - overrides both builtin & user_plugins_list (if there is a name clash)
        if LOCAL_PLUGINS_DIR.exists():
            local_components_list = [
                component_type for component_type
                in os.listdir(LOCAL_PLUGINS_DIR)
                if component_type not in ignored
            ]
            for component_type in local_components_list:
                component_map[component_type] = LOCAL_PLUGINS_DIR

        return component_map

    def import_plugin_module(self, component_name: str) -> AbstractModuleType:
        plugin_dir = self.component_map.get(component_name)
        if not plugin_dir:
            logger.error(f"plugin for {component_name} not found")
            sys.exit(1)
        basename = os.path.basename(plugin_dir)

        if basename == BUILTIN_PLUGINS_DIRNAME:
            # do relative import
            component_module = import_module(f'.{basename}.{component_name}',
                package="electrumsv_sdk")

        elif basename == USER_PLUGINS_DIRNAME:
            # do absolute import (SDK_HOME_DIR was added to sys.path to make this work)
            component_module = import_module(f'{basename}.{component_name}')

        elif basename == LOCAL_PLUGINS_DIRNAME:
            # do absolute import
            component_module = import_module(f'{basename}.{component_name}')

        component_module = cast(AbstractModuleType, component_module)
        return component_module

    def instantiate_plugin(self, config: Config) -> AbstractPlugin:
        """
        Each plugin must have a 'Plugin' class that is instantiated and has the main entrypoints:
        (install, start, stop, reset, status_check) as instance methods.
        """
        if not config.selected_component:  # i.e. if --id set
            component_dict = self.component_status_data_by_id(config.component_id)
            if component_dict:
                component_name = component_dict["component_type"]
            else:
                logger.exception("component_name not found")
        else:
            component_name = config.selected_component

        component_module = self.import_plugin_module(component_name)
        return component_module.Plugin(config)
