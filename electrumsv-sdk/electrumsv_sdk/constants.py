import os
from pathlib import Path

from .utils import get_sdk_datadir

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

# Directory structure
SDK_HOME_DIR: Path = get_sdk_datadir()
REMOTE_REPOS_DIR: Path = SDK_HOME_DIR.joinpath("remote_repos")
SHELL_SCRIPTS_DIR: Path = SDK_HOME_DIR.joinpath("shell_scripts")
DATADIR: Path = SDK_HOME_DIR.joinpath("component_datadirs")
LOGS_DIR: Path = SDK_HOME_DIR.joinpath("logs")
CONFIG_PATH: Path = SDK_HOME_DIR.joinpath("config.json")

# Three plugin locations
BUILTIN_PLUGINS_DIRNAME = 'builtin_components'
USER_PLUGINS_DIRNAME = 'user_plugins'
LOCAL_PLUGINS_DIRNAME = 'electrumsv_sdk_plugins'
BUILTIN_COMPONENTS_DIR: Path = Path(MODULE_DIR).joinpath(BUILTIN_PLUGINS_DIRNAME)
USER_PLUGINS_DIR: Path = SDK_HOME_DIR.joinpath(USER_PLUGINS_DIRNAME)
LOCAL_PLUGINS_DIR: Path = Path(os.getcwd()).joinpath(LOCAL_PLUGINS_DIRNAME)


class NameSpace:
    TOP_LEVEL = "top_level"
    INSTALL = "install"
    START = "start"
    STOP = "stop"
    RESET = "reset"
    NODE = "node"
    STATUS = 'status'


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


class ComponentLaunchFailedError(Exception):
    pass
