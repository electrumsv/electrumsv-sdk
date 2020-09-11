import json
import logging
import time

import requests

from .constants import STATUS_MONITOR_API
from .components import Component


class StatusMonitorClient:
    def __init__(self, app_state):
        self.app_state = app_state
        self.logger = logging.getLogger("status-monitor")

    def get_status(self):
        try:
            result = requests.get(STATUS_MONITOR_API + "/get_status")
            result.raise_for_status()
            return json.loads(result.json())
        except requests.exceptions.ConnectionError as e:
            self.logger.error("Problem fetching status: reason: " + str(e))
            return False

    def update_status(self, component: Component):
        for sleep_time in (3, 3, 3):
            try:
                result = requests.post(STATUS_MONITOR_API + "/update_status", json=component.to_dict())
                result.raise_for_status()
                return result
            except Exception as e:
                self.logger.error("Could not update status_monitor: reason: " + str(e))
                self.logger.debug("Retrying status update...")
                time.sleep(sleep_time)
        self.logger.error("failed to update status monitor")
