import os
import sys
from pathlib import Path
from typing import Optional

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


# copied from utils to avoid circular import
def get_sdk_datadir() -> Path:
    sdk_home_datadir = None
    if sys.platform == "win32":
        sdk_home_datadir = Path(os.environ["LOCALAPPDATA"]) / "ElectrumSV-SDK"
    if sdk_home_datadir is None:
        sdk_home_datadir = Path.home() / ".electrumsv-sdk"
    return sdk_home_datadir

# Directory structure
SDK_HOME_DIR: Path = get_sdk_datadir()
REMOTE_REPOS_DIR: Path = SDK_HOME_DIR.joinpath("remote_repos")
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
    INLINE = "inline"
    NEW_TERMINAL = "new_terminal"
    ID = "id"
    REPO = "repo"
    BRANCH = "branch"


class ComponentState(str):
    """If the user terminates an application without using the SDK, it will be registered as
    'Failed' status."""
    RUNNING = "Running"
    STOPPED = "Stopped"
    FAILED = "Failed"
    NONE = "None"

    @classmethod
    def from_str(cls, component_state_str: Optional[str]) -> str:
        if component_state_str == "Running":
            return cls.RUNNING
        elif component_state_str == "Stopped":
            return cls.STOPPED
        elif component_state_str == "Failed":
            return cls.FAILED
        elif component_state_str == 'None':
            return cls.NONE
        else:
            raise ValueError(f"ComponentState {component_state_str}, not recognised")

SUCCESS_EXITCODE = 0
SIGINT_EXITCODE = 130  # (2 + 128)
SIGKILL_EXITCODE = 137  # (9 + 128)


class NETWORKS:
    # do not change these names - must match cli args
    REGTEST = 'regtest'
    TESTNET = 'testnet'


NETWORKS_LIST = [NETWORKS.REGTEST, NETWORKS.TESTNET]
