import logging
import subprocess
import sys

from electrumsv_node import electrumsv_node

from .components import ComponentType, ComponentStore, ComponentName

logger = logging.getLogger("stoppers")


class Stoppers:
    def __init__(self, app_state):
        self.app_state = app_state
        self.component_store = ComponentStore(self.app_state)

    def stop_components_by_type(self, component_type: ComponentType):
        component_state = self.component_store.get_status()

        if component_type == ComponentType.NODE:
            electrumsv_node.stop()

        for component in component_state:
            if component_type == ComponentType.NODE:
                continue

            elif component["process_type"] == component_type:
                if sys.platform in ("linux", "darwin"):
                    subprocess.run(f"pkill -P {component['pid']}", shell=True)
                else:
                    subprocess.run(f"taskkill.exe /PID {component['pid']} /T /F")

    def stop(self):
        """if stop_set is empty, all processes terminate."""
        # todo: make this granular enough to pick out instances of each component type

        if ComponentName.NODE in self.app_state.stop_set or len(self.app_state.stop_set) == 0:
            self.stop_components_by_type(ComponentType.NODE)

        if ComponentName.ELECTRUMSV in self.app_state.stop_set or len(self.app_state.stop_set) == 0:
            self.stop_components_by_type(ComponentType.ELECTRUMSV)

        if ComponentName.ELECTRUMX in self.app_state.stop_set or len(self.app_state.stop_set) == 0:
            self.stop_components_by_type(ComponentType.ELECTRUMX)

        if ComponentName.INDEXER in self.app_state.stop_set or len(self.app_state.stop_set) == 0:
            self.stop_components_by_type(ComponentType.INDEXER)

        if ComponentName.STATUS_MONITOR in self.app_state.stop_set \
                or len(self.app_state.stop_set) == 0:
            self.stop_components_by_type(ComponentType.STATUS_MONITOR)

        logger.info(f"terminated: "
                    f"{self.app_state.stop_set if len(self.app_state.stop_set) != 0 else 'all'}")
