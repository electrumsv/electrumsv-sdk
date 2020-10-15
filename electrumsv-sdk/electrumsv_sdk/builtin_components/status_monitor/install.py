import logging
import os

from electrumsv_sdk.utils import make_shell_script_for_component


DEFAULT_PORT_ELECTRUMX = 5000
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENT_NAME = os.path.basename(MODULE_DIR)
logger = logging.getLogger(COMPONENT_NAME)


def generate_run_script_status_monitor(app_state):
    app_state.init_run_script_dir()
    commandline_string = (
        f"{app_state.python} " f"{app_state.status_monitor_dir.joinpath('server.py')}"
    )
    make_shell_script_for_component(COMPONENT_NAME, commandline_string, {})
