"""
all status changes for each component are persisted and read from component_state.json

STARTUP:
- immediate success is achieved (no exceptions at launch)    state=Running
- immediate failure occurs at launch                         state=Failed

SHUTDOWN
- on shutdown of an 'SDK component'                          state=Stopped

STATUS-MONITOR (server)
- pings SDK components periodically to see if they
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

- terminated components without using the SDK interface      state=Failed
"""
import enum
import json
import logging
import os
from typing import Optional, List

from electrumsv_sdk.utils import get_str_datetime
from filelock import FileLock


MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class ComponentName:
    STATUS_MONITOR = "status_monitor"
    NODE = "node"
    ELECTRUMX = "electrumx"
    ELECTRUMSV = "electrumsv"
    INDEXER = "indexer"


class ComponentOptions:
    NEW = "new"
    GUI = "gui"
    BACKGROUND = "background"
    ID = "id"
    REPO = "repo"
    BRANCH = "branch"


class ComponentType(enum.IntEnum):
    NODE = 1
    ELECTRUMX = 2
    ELECTRUMSV = 3
    INDEXER = 4
    STATUS_MONITOR = 5


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
        id: int,
        pid: int,
        process_type: ComponentType,
        endpoint: str,
        component_state: ComponentState,
        location: Optional[str],
        metadata: Optional[dict] = None,
        logging_path: Optional[str] = None,
    ):
        self.id = id  # human-readable identifier for instance
        self.pid = pid
        self.process_type = process_type
        self.endpoint = endpoint
        self.component_state = component_state
        self.location = location
        self.metadata = metadata
        self.logging_path = logging_path
        self.last_updated = get_str_datetime()

    def __repr__(self):
        return (
            f"Component(id={self.id}, pid={self.pid}, "
            f"process_type={self.process_type}, "
            f"endpoint={self.endpoint}, "
            f"component_state={self.component_state.name}, "
            f"location={self.location}, metadata={self.metadata}, "
            f"logging_path={self.logging_path}, last_updated={self.last_updated})"
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

    def get_status(self):
        filelock_logger = logging.getLogger("filelock")
        filelock_logger.setLevel(logging.WARNING)

        with self.file_lock:
            with open(self.component_state_path, "r") as f:
                component_state = json.loads(f.read())
        return component_state

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
