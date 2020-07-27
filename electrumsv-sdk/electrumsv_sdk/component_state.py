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
import logging
from typing import Optional


class ComponentName:
    NODE = "node"
    ELECTRUMX = "electrumx"
    ELECTRUMSV = "electrumsv"
    INDEXER = "indexer"


class ComponentType(enum.IntEnum):
    NODE = 1
    ELECTRUMX = 2
    ELECTRUMSV = 3
    INDEXER = 4


class ComponentState(enum.IntEnum):
    """
    'Running' and 'Stopped' are reserved for apps started/stopped via the SDK
    command-line interface.

    If the user terminates an application by other means, the SDK will assume something went
    wrong and will register it as 'Failed' status.
    """

    NONE = 0
    Running = 1
    Stopped = 2
    Failed = 3


class Component:
    def __init__(
        self,
        pid: int,
        process_name: ComponentName,
        process_type: ComponentType,
        endpoint: str,
        component_state: ComponentState,
        location: Optional[str],
        metadata: Optional[dict] = None,
        logging_path: Optional[str] = None,
    ):
        self.pid = pid
        self.process_name = process_name  # unique e.g. "electrumsv1" or "electrumsv2" if multiple
        self.process_type = process_type
        self.endpoint = endpoint
        self.component_state = component_state
        self.location = location
        self.metadata = metadata
        self.logging_path = logging_path

    def __repr__(self):
        return (
            f"Component(pid={self.pid}, process_name={self.process_name}, "
            f"process_type={self.process_type}, "
            f"endpoint={self.endpoint}, "
            f"component_state={(self.component_state.__str__().split('.')[1])}, "
            f"location={self.location}, metadata={self.metadata}, "
            f"logging_path={self.logging_path})"
        )

    def to_dict(self):
        config_dict = {}
        for key, val in self.__dict__.items():
            if key == 'component_state':
                val = self.component_state.__str__().split('.')[1]
            config_dict[key] = val
        return config_dict
