STATUS_MONITOR_GET_STATUS = "http://127.0.0.1:5000/api/status/get_status"
DEFAULT_PORT_ELECTRUMSV = 9999

BUILTIN_PLUGINS_DIRNAME = 'builtin_components'
USER_PLUGINS_DIRNAME = 'user_plugins'
LOCAL_PLUGINS_DIRNAME = 'electrumsv_sdk_plugins'


class ComponentLaunchFailedError(Exception):
    pass
