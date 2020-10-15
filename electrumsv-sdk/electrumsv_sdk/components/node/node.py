import subprocess
import sys

import electrumsv_node


def install(app_state):
    subprocess.run(f"{app_state.python} -m pip install electrumsv-node", shell=True, check=True)


def start(app_state):
    pass


def stop(app_state):
    pass


def reset(app_state):
    pass


def status_check(app_state):
    pass
