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
import enum
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List, Union

from filelock import FileLock

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger("component-store")


def get_str_datetime():
    return datetime.datetime.now().strftime(TIME_FORMAT)


class ComponentName:
    WHATSONCHAIN = "whatsonchain"
    STATUS_MONITOR = "status_monitor"
    NODE = "node"
    ELECTRUMX = "electrumx"
    ELECTRUMSV = "electrumsv"
    INDEXER = "indexer"

    def __add__(self, val):
        return str(self) + str(val)

class ComponentOptions:
    NEW = "new"
    GUI = "gui"
    BACKGROUND = "background"
    ID = "id"
    REPO = "repo"
    BRANCH = "branch"


class ComponentState(enum.IntEnum):
    """If the user terminates an application without using the SDK, it will be registered as
    'Failed' status."""
    NONE = 0
    Running = 1
    Stopped = 2
    Failed = 3


class Component:
    def __init__(
        self,
        id: str,
        pid: int,
        component_type: ComponentName,
        location: Union[str, Path],
        status_endpoint: str,
        component_state: Optional[ComponentState]=ComponentState.Running,
        metadata: Optional[dict] = None,
        logging_path: Optional[Union[str, Path]] = None,
    ):
        self.id = id  # human-readable identifier for instance
        self.pid = pid
        self.component_type = component_type
        self.status_endpoint = status_endpoint
        self.component_state = component_state
        self.location = str(location)
        self.metadata = metadata
        self.logging_path = str(logging_path)
        self.last_updated = get_str_datetime()

    def __repr__(self):
        return (
            f"Component(id={self.id}, pid={self.pid}, "
            f"component_type={self.component_type}, "
            f"status_endpoint={self.status_endpoint}, "
            f"component_state={self.component_state.name}, "
            f"location={self.location}, metadata={self.metadata}, "
            f"logging_path={self.logging_path}, "
            f"last_updated={self.last_updated})"
        )

    def to_dict(self):
        config_dict = {}
        for key, val in self.__dict__.items():
            if key == "component_state":
                val = self.component_state.name
            config_dict[key] = val
        return config_dict


class ComponentStore:
    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.file_path = "component_state.json"
        self.lock_path = app_state.electrumsv_sdk_data_dir / "component_state.json.lock"
        self.file_lock = FileLock(self.lock_path, timeout=1)
        self.component_state_path = app_state.electrumsv_sdk_data_dir / self.file_path
        # todo include extention plugin directory (in AppData/Local/ElectrumSV-SDK/builtin_components)
        self.component_list = os.listdir(self.app_state.plugin_dir)

    def get_component_data_dir(self, component_name: ComponentName, data_dir_parent:
            Path, id=None):
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

        new = self.app_state.start_options[ComponentOptions.NEW]
        if not id:
            id = self.app_state.start_options[ComponentOptions.ID]

        # autoincrements (electrumsv1 -> electrumsv2 -> electrumsv3...) until empty space is found
        if is_new_and_no_id(id, new):
            count = 1
            while True:
                self.app_state.start_options[ComponentOptions.ID] = id = \
                    str(component_name) + str(count)
                new_dir = data_dir_parent.joinpath(id)
                if not new_dir.exists():
                    break
                else:
                    count += 1
            logger.debug(f"Using new user-specified electrumsv data dir ({id})")

        elif is_new_and_id(id, new):
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            if new_dir.exists():
                logger.debug(f"User-specified electrumsv data directory: {new_dir} already exists ("
                      f"either drop the --new flag or choose a unique identifier).")
                sys.exit(1)
            logger.debug(f"Using user-specified electrumsv data dir ({new_dir})")

        elif is_not_new_and_id(id, new):
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            if not new_dir.exists():
                logger.debug(f"User-specified electrumsv data directory: {new_dir} does not exist"
                             f" and so will be created anew.")
            logger.debug(f"Using user-specified electrumsv data dir ({new_dir})")

        elif is_not_new_and_no_id(id, new):
            id = self.app_state.get_id(component_name)
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            logger.debug(f"Using default electrumsv data dir ({new_dir})")

        logger.debug(f"Electrumsv data dir = {new_dir}")
        return new_dir

    def get_status(self):
        filelock_logger = logging.getLogger("filelock")
        filelock_logger.setLevel(logging.WARNING)

        with self.file_lock:
            if self.component_state_path.exists():
                with open(self.component_state_path, "r") as f:
                    component_state = json.loads(f.read())
                return component_state
            else:
                return []

    def find_component_if_exists(self, component: Component, component_state: List[dict]):
        for index, comp in enumerate(component_state):
            if comp.get("id") == component.id:
                return (index, component)
        return False

    def update_status_file(self, component):
        """updates to the *file* (component.json) - does *not* update the server"""

        component_state = []
        with self.file_lock:
            if self.component_state_path.exists():
                with open(self.component_state_path, "r") as f:
                    data = f.read()
                    if data:
                        component_state = json.loads(data)

        result = self.find_component_if_exists(component, component_state)
        if not result:
            component_state.append(component.to_dict())
        else:
            index, component = result
            component_state[index] = component.to_dict()

        with open(self.component_state_path, "w") as f:
            f.write(json.dumps(component_state, indent=4))

    def component_status_data_by_id(self, component_id):
        component_state = self.get_status()
        for component in component_state:
            if component.get('id') == component_id:
                return component

        logger.error("component id not found")
        return {}

    def derive_shell_script_path(self, component_name):
        script_name = component_name

        if sys.platform == "win32":
            script = self.app_state.run_scripts_dir.joinpath(f"{script_name}.bat")
        elif sys.platform in ("linux", "darwin"):
            script = self.app_state.run_scripts_dir.joinpath(f"{script_name}.sh")
        return script
