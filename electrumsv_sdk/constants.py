import logging
import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

sdk_log_level = os.environ.get("SDK_LOG_LEVEL", 'INFO')
if sdk_log_level.upper() == 'DEBUG':
    LOG_LEVEL = logging.DEBUG
if sdk_log_level.upper() == 'INFO':
    LOG_LEVEL = logging.INFO
if sdk_log_level.upper() == 'WARNING':
    LOG_LEVEL = logging.WARNING
if sdk_log_level.upper() == 'ERROR':
    LOG_LEVEL = logging.ERROR
if sdk_log_level.upper() == 'CRITICAL':
    LOG_LEVEL = logging.CRITICAL


# copied from utils to avoid circular import
def get_sdk_datadir() -> Path:
    sdk_home_datadir = None
    if sys.platform == "win32":
        sdk_home_datadir = Path(os.environ["LOCALAPPDATA"]) / "ElectrumSV-SDK"
    if sdk_home_datadir is None:
        sdk_home_datadir = Path.home() / ".electrumsv-sdk"
    return sdk_home_datadir


# copied from utils to avoid circular import
def read_config_json() -> Dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            data = f.read()
            if data.strip():
                config = json.loads(data)
            else:
                config = {}

        return config
    else:
        return {}


def get_dynamic_datadir() -> Path:
    sdk_home_dir = get_sdk_datadir()
    # Check config.json (which needs to *always* be located in the system home directory at
    # initial startup) to see if a portable / local directory has been set for SDK_HOME_DIR
    config = read_config_json()
    modified_sdk_home_dir = config.get("sdk_home_dir")
    if modified_sdk_home_dir:
        sdk_home_dir = Path(modified_sdk_home_dir)
    return sdk_home_dir

# Config file location cannot change
CONFIG_PATH: Path = get_sdk_datadir().joinpath("config.json")

# Dynamic file locations (can be changed for portability)
SDK_HOME_DIR: Path = get_dynamic_datadir()
REMOTE_REPOS_DIR: Path = SDK_HOME_DIR.joinpath("remote_repos")
DATADIR: Path = SDK_HOME_DIR.joinpath("component_datadirs")
LOGS_DIR: Path = SDK_HOME_DIR.joinpath("logs")
PYTHON_LIB_DIR: Path = SDK_HOME_DIR.joinpath("python_libs")

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
    CONFIG = 'config'


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
