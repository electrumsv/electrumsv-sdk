STATUS_MONITOR_GET_STATUS = "http://127.0.0.1:5000/api/status/get_status"
STATUS_MONITOR_UPDATE_STATUS = "http://127.0.0.1:5000/api/status/update_status"
DEFAULT_PORT_ELECTRUMSV = 9999


class ComponentLaunchFailedError(Exception):
    pass
