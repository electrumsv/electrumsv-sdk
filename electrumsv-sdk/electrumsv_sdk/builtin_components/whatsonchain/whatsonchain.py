import logging
import os

from electrumsv_sdk.components import ComponentOptions

from .install import fetch_whatsonchain, generate_run_script_whatsonchain, packages_whatsonchain

DEFAULT_PORT_WHATSONCHAIN = 3002
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENT_NAME = os.path.basename(MODULE_DIR)
logger = logging.getLogger(COMPONENT_NAME)


def install(app_state):
    repo = app_state.start_options[ComponentOptions.REPO]
    if not repo == "":  # default
        logger.error("ignoring --repo flag for whatsonchain - not applicable.")

    # 1) configure_paths_and_datadir (SEE BELOW)
    app_state.woc_dir = app_state.depends_dir.joinpath("woc-explorer")

    # 2) fetch (as needed) (SEE BELOW)
    fetch_whatsonchain(app_state)

    # 3) pip install (or npm install) packages/dependencies (SEE BELOW)
    packages_whatsonchain(app_state)

    # 4) generate run script (SEE BELOW)
    generate_run_script_whatsonchain(app_state)


def start(app_state):
    pass


def stop(app_state):
    pass


def reset(app_state):
    pass


def status_check(app_state):
    pass
