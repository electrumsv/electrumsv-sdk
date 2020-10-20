import json
import logging
import requests

from .constants import STATUS_MONITOR_GET_STATUS


class StatusMonitorClient:
    def __init__(self, app_state):
        self.app_state = app_state
        self.logger = logging.getLogger("status-monitor")

    def get_status(self):
        try:
            result = requests.get(STATUS_MONITOR_GET_STATUS + "/get_status")
            result.raise_for_status()
            return json.loads(result.json())
        except requests.exceptions.ConnectionError as e:
            self.logger.error("Problem fetching status: reason: " + str(e))
            return False
