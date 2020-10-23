import logging
import os

from electrumsv_sdk.utils import get_directory_name

DEFAULT_PORT = 5000
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def generate_run_script(app_state):
    os.makedirs(app_state.shell_scripts_dir, exist_ok=True)
    os.chdir(app_state.shell_scripts_dir)
    line1 = (
        f"{app_state.python} " f"{app_state.status_monitor_dir.joinpath('server.py')}"
    )
    app_state.make_shell_script_for_component(list_of_shell_commands=[line1],
        component_name=COMPONENT_NAME)
