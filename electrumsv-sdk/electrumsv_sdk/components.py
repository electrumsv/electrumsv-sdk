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
from pathlib import Path
from typing import Optional, List, Union, Dict, Tuple

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


class ComponentState:
    """If the user terminates an application without using the SDK, it will be registered as
    'Failed' status."""
    RUNNING = "Running"
    STOPPED = "Stopped"
    FAILED = "Failed"


class Component:
    def __init__(
        self,
        id: str,
        pid: int,
        component_type: str,
        location: Union[str, Path],
        status_endpoint: str,
        component_state:
            Union[ComponentState.RUNNING, ComponentState.STOPPED, ComponentState.FAILED] = None,
        metadata: Optional[dict] = None,
        logging_path: Optional[Union[str, Path]] = None,
    ):
        self.id = id  # human-readable identifier for instance
        self.pid = pid
        self.component_type = str(component_type)
        self.status_endpoint = status_endpoint
        self.component_state = str(component_state)
        self.location = str(location)
        self.metadata = metadata
        self.logging_path = str(logging_path)
        self.last_updated = get_str_datetime()

    def __repr__(self):
        return (
            f"Component(id={self.id}, pid={self.pid}, "
            f"component_type={self.component_type}, "
            f"status_endpoint={self.status_endpoint}, "
            f"component_state={self.component_state}, "
            f"location={self.location}, metadata={self.metadata}, "
            f"logging_path={self.logging_path}, "
            f"last_updated={self.last_updated})"
        )

    def to_dict(self):
        config_dict = {}
        for key, val in self.__dict__.items():
            config_dict[key] = val
        return config_dict

    @classmethod
    def from_dict(cls, component_dict: Dict):
        component_dict.pop('last_updated')
        return cls(**component_dict)


class ComponentStore:
    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.file_path = "component_state.json"
        self.lock_path = app_state.sdk_home_dir / "component_state.json.lock"
        self.file_lock = FileLock(self.lock_path, timeout=1)
        self.component_state_path = app_state.sdk_home_dir / self.file_path
        self.component_list = [
            component_type for component_type
            in os.listdir(self.app_state.builtin_components_dir)
            if component_type not in {'__init__.py', '__pycache__'}
        ]

    def get_component_data_dir(self, component_name: ComponentName):
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

        new = self.app_state.global_cli_flags[ComponentOptions.NEW]
        id = self.app_state.global_cli_flags[ComponentOptions.ID]

        # autoincrement <component_name>1 -> <component_name>2 etc. new datadir is found
        if is_new_and_no_id(id, new):
            count = 1
            while True:
                self.app_state.global_cli_flags[ComponentOptions.ID] = id = \
                    str(component_name) + str(count)
                new_dir = self.app_state.data_dir.joinpath(f"{component_name}/{id}")
                if not new_dir.exists():
                    break
                else:
                    count += 1
            logger.debug(f"Using new user-specified data dir ({id})")

        elif is_new_and_id(id, new):
            new_dir = self.app_state.data_dir.joinpath(f"{component_name}/{id}")
            if new_dir.exists():
                logger.debug(f"User-specified data directory: {new_dir} already exists ("
                      f"either drop the --new flag or choose a unique identifier).")
                sys.exit(1)
            logger.debug(f"Using user-specified data dir ({new_dir})")

        elif is_not_new_and_id(id, new):
            new_dir = self.app_state.data_dir.joinpath(f"{component_name}/{id}")
            if not new_dir.exists():
                logger.debug(f"User-specified data directory: {new_dir} does not exist"
                             f" and so will be created anew.")
            logger.debug(f"Using user-specified data dir ({new_dir})")

        elif is_not_new_and_no_id(id, new):
            id = self.app_state.get_id(component_name)  # default
            new_dir = self.app_state.data_dir.joinpath(f"{component_name}/{id}")
            logger.debug(f"Using default data dir ({new_dir})")

        logger.debug(f"data dir = {new_dir}")
        return new_dir

    def get_status(self) -> List[Dict]:
        filelock_logger = logging.getLogger("filelock")
        filelock_logger.setLevel(logging.WARNING)

        with self.file_lock:
            if self.component_state_path.exists():
                with open(self.component_state_path, "r") as f:
                    data = f.read()
                    if data:
                        component_state = json.loads(data)
                    else:
                        component_state = []
                return component_state
            else:
                return []

    def find_component_if_exists(self, id: str, component_state: List[dict]) \
            -> Optional[Tuple[int, Dict]]:
        for index, comp in enumerate(component_state):
            if comp.get("id") == id:
                return (index, comp)

    def update_status_file(self, component_info: Component):
        """updates to the *file* (component.json) - does *not* update the server"""

        component_state = []
        with self.file_lock:
            if self.component_state_path.exists():
                with open(self.component_state_path, "r") as f:
                    data = f.read()
                    if data:
                        component_state = json.loads(data)
                    else:
                        component_state = []

        result = self.find_component_if_exists(component_info.id, component_state)
        if not result:
            component_state.append(component_info.to_dict())
        else:
            index, _component_dict = result
            component_state[index] = component_info.to_dict()

        with open(self.component_state_path, "w") as f:
            f.write(json.dumps(component_state, indent=4))

    def component_status_data_by_id(self, component_id: str) -> Dict:
        component_state = self.get_status()
        for component in component_state:
            if component.get('id') == component_id:
                return component

        logger.error("component id not found")
        return {}
