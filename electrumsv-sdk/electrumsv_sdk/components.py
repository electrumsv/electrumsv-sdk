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
from pathlib import Path
from typing import Optional, Union, Dict

from filelock import FileLock

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger("component-store")


def get_str_datetime():
    return datetime.datetime.now().strftime(TIME_FORMAT)


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
        self.file_name = "component_state.json"
        self.lock_path = app_state.sdk_home_dir / "component_state.json.lock"
        self.file_lock = FileLock(self.lock_path, timeout=5)
        self.component_state_path = app_state.sdk_home_dir / self.file_name
        if not self.component_state_path.exists():
            open(self.component_state_path, 'w').close()

    def get_status(self) -> Dict:
        filelock_logger = logging.getLogger("filelock")
        filelock_logger.setLevel(logging.WARNING)

        with self.file_lock:
            if self.component_state_path.exists():
                with open(self.component_state_path, "r") as f:
                    data = f.read()
                    if data:
                        component_state = json.loads(data)
                    else:
                        component_state = {}
                return component_state
            else:
                return {}

    def update_status_file(self, new_component_info: Component):
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
        logger.debug(f"updated status: {new_component_info}")

    def component_status_data_by_id(self, component_id: str) -> Dict:
        component_state = self.get_status()
        component_info = component_state.get(component_id)
        if component_info:
            return component_info
        logger.error("component id not found")
        return {}
