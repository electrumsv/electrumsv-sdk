import json
import logging
import os
from pathlib import Path
import shutil
import stat
import sys

from electrumsv_node import electrumsv_node

from .argparsing import ArgParser
from .config import Config
from .constants import SDK_HOME_DIR, REMOTE_REPOS_DIR, DATADIR, LOGS_DIR, \
    USER_PLUGINS_DIR, CONFIG_PATH
from .controller import Controller

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger("app_state")
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)
orm_logger = logging.getLogger("peewee")
orm_logger.setLevel(logging.WARNING)


class AppState:
    """Global application state"""

    def __init__(self):
        os.makedirs(REMOTE_REPOS_DIR, exist_ok=True)
        os.makedirs(DATADIR, exist_ok=True)
        os.makedirs(LOGS_DIR, exist_ok=True)
        os.makedirs(USER_PLUGINS_DIR, exist_ok=True)
        self.calling_context_dir: Path = Path(os.getcwd())
        self.sdk_package_dir: Path = Path(MODULE_DIR)

        # plugins
        sys.path.append(str(self.sdk_package_dir))  # for dynamic import of builtin_components
        sys.path.append(f"{SDK_HOME_DIR}")  # for dynamic import of user_components
        sys.path.append(f"{self.calling_context_dir}")  # for dynamic import of local plugins

        self.argparser = ArgParser()
        self.argparser.manual_argparsing(sys.argv)
        self.config: Config = self.argparser.generate_immutable_config()
        self.argparser.validate_cli_args()
        self.controller = Controller(self)

    def purge_prev_installs_if_exist(self) -> None:
        def remove_readonly(func, path, excinfo):  # .git is read-only
            os.chmod(path, stat.S_IWRITE)
            func(path)

        if REMOTE_REPOS_DIR.exists():
            shutil.rmtree(REMOTE_REPOS_DIR, onerror=remove_readonly)
            os.makedirs(REMOTE_REPOS_DIR, exist_ok=True)

    def handle_first_ever_run(self) -> None:
        try:
            with open(CONFIG_PATH, "r") as f:
                data = f.read()
                if data:
                    config = json.loads(data)
                else:
                    config = {}
        except FileNotFoundError:
            with open(CONFIG_PATH, "w") as f:
                config = {"is_first_run": True}
                f.write(json.dumps(config, indent=4))

        if config.get("is_first_run") or config.get("is_first_run") is None:
            logger.debug(
                "Running SDK for the first time. please wait for configuration to complete..."
            )
            with open(CONFIG_PATH, "w") as f:
                config = {"is_first_run": False}
                f.write(json.dumps(config, indent=4))

            electrumsv_node.reset()
