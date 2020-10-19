import logging
import subprocess
from pathlib import Path

from electrumsv_node import electrumsv_node

from electrumsv_sdk.utils import get_directory_name, get_component_port

DEFAULT_PORT_NODE = 18332
DEFAULT_P2P_PORT_NODE = 18444
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def configure_paths(app_state, repo=None, branch=None):
    app_state.component_source_dir = Path(electrumsv_node.FILE_PATH).parent
    app_state.component_port = get_component_port(DEFAULT_PORT_NODE)
    app_state.component_p2p_port = get_component_port(DEFAULT_P2P_PORT_NODE)
    app_state.component_datadir = app_state.get_component_datadir(COMPONENT_NAME)


def fetch_node(app_state):
    subprocess.run(f"{app_state.python} -m pip install electrumsv-node", shell=True, check=True)
