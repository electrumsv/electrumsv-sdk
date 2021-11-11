import logging
import os
from typing import Optional

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
SIGINT_EXITCODE_LINUX = -2
SIGKILL_EXITCODE_LINUX = -9


class NETWORKS:
    # do not change these names - must match cli args
    REGTEST = 'regtest'
    TESTNET = 'testnet'


NETWORKS_LIST = [NETWORKS.REGTEST, NETWORKS.TESTNET]
