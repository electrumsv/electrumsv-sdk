import json
import logging
import subprocess

from electrumsv_node import electrumsv_node

from .components import ComponentType, ComponentStore

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
                subprocess.run(f"taskkill.exe /PID {component['pid']} /T /F")

    def stop(self):
        self.stop_components_by_type(ComponentType.NODE)
        self.stop_components_by_type(ComponentType.ELECTRUMSV)
        self.stop_components_by_type(ComponentType.ELECTRUMX)
        self.stop_components_by_type(ComponentType.STATUS_MONITOR)
        print("stack terminated")
