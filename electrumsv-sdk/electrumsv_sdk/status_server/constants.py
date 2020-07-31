import os
from pathlib import Path

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

FILE_LOCK_PATH = Path(MODULE_DIR).parent.joinpath("component_state.json.lock").__str__()
COMPONENT_STATE_PATH = (Path(MODULE_DIR).parent.joinpath("component_state.json").__str__())