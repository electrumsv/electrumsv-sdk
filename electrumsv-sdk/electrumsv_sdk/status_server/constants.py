import os
from pathlib import Path

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

FILE_LOCK_PATH = str(Path(MODULE_DIR).parent.joinpath("component_state.json.lock"))
COMPONENT_STATE_PATH = str(Path(MODULE_DIR).parent.joinpath("component_state.json"))
