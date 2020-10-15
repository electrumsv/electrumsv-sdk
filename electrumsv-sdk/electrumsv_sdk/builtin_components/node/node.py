import logging
import os
from pathlib import Path

from electrumsv_sdk.components import ComponentOptions

from .install import fetch_node


MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENT_NAME = os.path.basename(MODULE_DIR)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    """The node component has a pip installer at https://pypi.org/project/electrumsv-node/ and
    only official releases from pypi are supported"""
    repo = app_state.start_options[ComponentOptions.REPO]
    if not repo == "":  # default
        logger.error("ignoring --repo flag for node - not applicable.")

    # 1) configure_paths_and_maps - (NOT APPLICABLE)
    # 2) fetch (as needed) - (SEE BELOW)
    fetch_node(app_state)
    # 3) pip install (or npm install) packages/dependencies - (NOT APPLICABLE)
    # 4) generate run script - (NOT APPLICABLE)


def start(app_state):
    pass


def stop(app_state):
    pass


def reset(app_state):
    pass


def status_check(app_state):
    pass
