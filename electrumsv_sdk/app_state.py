import json
import logging
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import List, Callable, Any

from electrumsv_node import electrumsv_node

from .argparsing import ArgParser
from .config import Config
from .constants import NameSpace
from .controller import Controller

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger("app_state")
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)
orm_logger = logging.getLogger("peewee")
orm_logger.setLevel(logging.WARNING)


class AppState:
    """Global application state"""

    def __init__(self, arguments: List[str]):
        self.argparser = ArgParser()
        self.argparser.manual_argparsing(arguments)  # allows library to inject args (vs sys.argv)
        self.cli_inputs = self.argparser.generate_config()
        self.config = Config(cli_inputs=self.cli_inputs)
        if self.cli_inputs.namespace == NameSpace.CONFIG:
            self.config.print_json()
        logger.debug(f"\nConfiguration: \n"
            f"\tSDK_HOME_DIR={self.config.SDK_HOME_DIR}\n"
            f"\tREMOTE_REPOS_DIR={self.config.REMOTE_REPOS_DIR}\n"
            f"\tDATADIR={self.config.DATADIR}\n"
            f"\tLOGS_DIR={self.config.LOGS_DIR}\n"
            f"\tPYTHON_LIB_DIR={self.config.PYTHON_LIB_DIR}\n")

        self.argparser.validate_cli_args()

        self.calling_context_dir: Path = Path(os.getcwd())
        self.sdk_package_dir: Path = Path(MODULE_DIR)

        # Ensure all three plugin locations are importable
        sys.path.append(str(self.sdk_package_dir))  # builtin_components
        sys.path.append(f"{self.config.SDK_HOME_DIR}")  # user_components
        sys.path.append(f"{self.calling_context_dir}")  # local plugins

        self.controller = Controller(self)

    def purge_prev_installs_if_exist(self) -> None:
        def remove_readonly(func: Callable[[Path], None], path: Path, excinfo: Any) -> None:
            os.chmod(path, stat.S_IWRITE)
            func(path)

        assert self.config.REMOTE_REPOS_DIR is not None
        if self.config.REMOTE_REPOS_DIR.exists():
            shutil.rmtree(self.config.REMOTE_REPOS_DIR, onerror=remove_readonly)
            os.makedirs(self.config.REMOTE_REPOS_DIR, exist_ok=True)

    def handle_first_ever_run(self) -> None:
        assert self.config.CONFIG_PATH is not None
        try:
            with open(self.config.CONFIG_PATH, "r") as f:
                data = f.read()
                if data:
                    config = json.loads(data)
                else:
                    config = {}
        except FileNotFoundError:
            with open(self.config.CONFIG_PATH, "w") as f:
                config = {"is_first_run": True}
                f.write(json.dumps(config, indent=4))

        if config.get("is_first_run") or config.get("is_first_run") is None:
            logger.debug(
                "Running SDK for the first time. please wait for configuration to complete..."
            )
            with open(self.config.CONFIG_PATH, "w") as f:
                config = {"is_first_run": False}
                f.write(json.dumps(config, indent=4))

            electrumsv_node.reset()
