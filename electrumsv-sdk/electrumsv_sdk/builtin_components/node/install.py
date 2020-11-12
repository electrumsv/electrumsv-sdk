import logging
import subprocess
from pathlib import Path

from electrumsv_node import electrumsv_node

from electrumsv_sdk.utils import get_directory_name

from . import env

DEFAULT_PORT = 18332
DEFAULT_P2P_PORT_NODE = 18444
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def configure_paths(app_state, repo=None, branch=None):
    app_state.component_source_dir = Path(electrumsv_node.FILE_PATH).parent
    if not app_state.component_datadir:
        app_state.component_datadir, app_state.component_id = \
            app_state.get_component_datadir(COMPONENT_NAME)

    app_state.component_port = app_state.get_component_port(DEFAULT_PORT, COMPONENT_NAME,
                                                            app_state.component_id)
    app_state.component_p2p_port = app_state.get_component_port(DEFAULT_P2P_PORT_NODE,
        COMPONENT_NAME, app_state.component_id)

    # env vars take precedence for port and dbdir
    if env.NODE_PORT:
        app_state.component_port = env.NODE_PORT


def fetch_node(app_state):
    subprocess.run(f"{app_state.python} -m pip install electrumsv-node", shell=True, check=True)
