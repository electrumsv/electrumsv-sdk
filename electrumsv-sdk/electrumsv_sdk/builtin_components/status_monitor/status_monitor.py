import logging
import os
from pathlib import Path

from electrumsv_sdk.components import ComponentOptions

from .install import generate_run_script_status_monitor


DEFAULT_PORT_ELECTRUMX = 51001
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENT_NAME = os.path.basename(MODULE_DIR)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    """this is a locally hosted sub-repo so there is no 'fetch' or 'package' installation steps"""
    repo = app_state.start_options[ComponentOptions.REPO]
    if not repo == "":  # default
        logger.error("ignoring --repo flag for status_monitor - not applicable.")

    # 1) configure_paths_and_maps - (NOT APPLICABLE)
    # 2) fetch (as needed) - (NOT APPLICABLE)
    # 3) pip install (or npm install) packages/dependencies - (NOT APPLICABLE)
    # 4) generate run script - (SEE BELOW)
    generate_run_script_status_monitor(app_state)


def start(app_state):
    pass


def stop(app_state):
    pass


def reset(app_state):
    pass


def status_check(app_state):
    pass
