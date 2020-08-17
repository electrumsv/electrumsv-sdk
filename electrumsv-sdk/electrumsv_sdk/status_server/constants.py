import os
from pathlib import Path
import sys


def _get_data_path() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA")) / "ElectrumSV-SDK"
    return Path.home() / ".electrumsv-sdk"


DATA_PATH = _get_data_path()
FILE_LOCK_PATH = DATA_PATH / "component_state.json.lock"
COMPONENT_STATE_PATH = DATA_PATH / "component_state.json"
