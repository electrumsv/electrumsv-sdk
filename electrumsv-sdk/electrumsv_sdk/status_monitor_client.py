import logging

import requests

from .constants import STATUS_MONITOR_API
from .components import Component


class StatusMonitorClient:

    def __init__(self, app_state):
        self.app_state = app_state
        self.logger = logging.getLogger("status-monitor")

    def update_status(self, component: Component):
        try:
            result = requests.post(STATUS_MONITOR_API + "/update_status", json=component.to_dict())
            result.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.logger.error("could not update status_monitor: reason: " + str(e))
