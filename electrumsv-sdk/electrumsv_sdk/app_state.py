import argparse
import json
import logging
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Dict, List, Optional

from electrumsv_node import electrumsv_node

from .starters import Starters
from .stoppers import Stoppers
from .installers import Installers
from .constants import DEFAULT_PORT_ELECTRUMSV
from .argparsing import ArgParser
from .components import ComponentName, ComponentOptions, ComponentStore
from .controller import Controller
from .handlers import Handlers
from .reset import Resetters
from .status_monitor_client import StatusMonitorClient

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger("status")
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)


class AppState:
    """Only electrumsv paths are saved to config.json so that 'reset' works on correct wallet."""

    def __init__(self):
        data_dir = None
        if sys.platform == "win32":
            data_dir = Path(os.environ.get("LOCALAPPDATA")) / "ElectrumSV-SDK"
        if data_dir is None:
            data_dir = Path.home() / ".electrumsv-sdk"

        self.electrumsv_sdk_data_dir = data_dir
        self.plugin_dir = Path(MODULE_DIR).joinpath("components")

        self.component_store = ComponentStore(self)
        self.arparser = ArgParser(self)
        self.starters = Starters(self)
        self.stoppers = Stoppers(self)
        self.controller = Controller(self)
        self.handlers = Handlers(self)
        self.installers = Installers(self)
        self.resetters = Resetters(self)
        self.status_monitor_client = StatusMonitorClient(self)

        # namespaces
        self.NAMESPACE = ""  # 'start', 'stop' or 'reset'

        self.TOP_LEVEL = "top_level"
        self.START = "start"
        self.STOP = "stop"
        self.RESET = "reset"
        self.NODE = "node"
        self.STATUS = "status"

        self.subcmd_map: Dict[str, argparse.ArgumentParser] = {}  # cmd_name: ArgumentParser
        self.subcmd_raw_args_map: Dict[str, List[str]] = {}  # cmd_name: raw arguments
        self.subcmd_parsed_args_map = {}  # cmd_name: parsed arguments
        self.component_args = []  # e.g. store arguments to pass to the electrumsv's cli interface

        self.depends_dir = self.electrumsv_sdk_data_dir.joinpath("sdk_depends")
        self.run_scripts_dir = self.electrumsv_sdk_data_dir.joinpath("run_scripts")
        self.electrumsv_sdk_config_path = self.electrumsv_sdk_data_dir.joinpath("config.json")

        # electrumsv paths are set dynamically at startup - see: set_electrumsv_paths()
        self.electrumsv_data_dir_init = Path(MODULE_DIR).joinpath("components").joinpath(
            "electrumsv").joinpath("data_dir_init").joinpath("regtest")

        self.electrumsv_dir = None
        self.electrumsv_data_dir = None
        self.electrumsv_regtest_dir = None
        self.electrumsv_regtest_config_path = None
        self.electrumsv_regtest_wallets_dir = None
        self.electrumsv_requirements_path = None
        self.electrumsv_binary_requirements_path = None

        self.woc_dir = self.depends_dir.joinpath("woc-explorer")

        self.sdk_package_dir = Path(MODULE_DIR)
        self.status_monitor_dir = self.sdk_package_dir.joinpath("status_server")
        self.status_monitor_logging_path = self.electrumsv_sdk_data_dir.joinpath("logs").joinpath(
            "status_monitor")
        os.makedirs(self.status_monitor_logging_path, exist_ok=True)

        self.selected_start_component: Optional[ComponentName] = None
        self.selected_stop_component: Optional[ComponentName] = None
        self.selected_reset_component: Optional[ComponentName] = None

        self.start_options: Dict[ComponentName] = {}
        self.node_args = None

        self.start_options[ComponentOptions.NEW] = False
        self.start_options[ComponentOptions.GUI] = False
        self.start_options[ComponentOptions.BACKGROUND] = False
        self.start_options[ComponentOptions.ID] = ""
        self.start_options[ComponentOptions.REPO] = ""
        self.start_options[ComponentOptions.BRANCH] = ""

    def get_id(self, component_name: ComponentName):
        id = self.start_options[ComponentOptions.ID]
        if not id:  # Default component_name
            id = component_name + "1"
        return id

    def set_electrumsv_paths(self, electrumsv_dir: Path):
        """This is set dynamically at startup. It is *only persisted for purposes of the 'reset'
        command. The trade-off is that the electrumsv 'repo' will need to be specified anew every
        time the SDK 'start' command is run."""
        self.electrumsv_dir = electrumsv_dir
        id = self.get_id(ComponentName.ELECTRUMSV)
        self.update_electrumsv_data_dir(self.electrumsv_dir.joinpath(id),
            DEFAULT_PORT_ELECTRUMSV)
        self.electrumsv_requirements_path = (
            self.electrumsv_dir.joinpath("contrib")
            .joinpath("deterministic-build")
            .joinpath("requirements.txt")
        )
        self.electrumsv_binary_requirements_path = (
            self.electrumsv_dir.joinpath("contrib")
            .joinpath("deterministic-build")
            .joinpath("requirements-binaries.txt")
        )

    def update_electrumsv_data_dir(self, electrumsv_data_dir, port):
        self.electrumsv_data_dir = electrumsv_data_dir
        self.electrumsv_regtest_dir = electrumsv_data_dir.joinpath("regtest")
        self.electrumsv_regtest_config_path = self.electrumsv_regtest_dir.joinpath("config")
        self.electrumsv_regtest_wallets_dir = self.electrumsv_regtest_dir.joinpath("wallets")

        self.electrumsv_port = port

    def save_repo_paths(self):
        """overwrites config.json"""
        config_path = self.electrumsv_sdk_config_path
        with open(config_path, "r") as f:
            config = json.loads(f.read())

        with open(config_path, "w") as f:
            config["electrumsv_dir"] = str(self.electrumsv_dir)
            f.write(json.dumps(config, indent=4))

    def load_repo_paths(self) -> "self":
        """loads state from config.json"""
        config_path = self.electrumsv_sdk_config_path
        with open(config_path, "r") as f:
            config = json.loads(f.read())
            electrumsv_dir = config.get("electrumsv_dir")
            if electrumsv_dir:
                self.set_electrumsv_paths(Path(electrumsv_dir))
            else:
                self.set_electrumsv_paths(Path(self.depends_dir.joinpath("electrumsv")))

    def purge_prev_installs_if_exist(self):
        def remove_readonly(func, path, excinfo):  # .git is read-only
            os.chmod(path, stat.S_IWRITE)
            func(path)

        if self.depends_dir.exists():
            shutil.rmtree(self.depends_dir, onerror=remove_readonly)
            os.makedirs(self.depends_dir, exist_ok=True)
        if self.run_scripts_dir.exists():
            shutil.rmtree(self.run_scripts_dir, onerror=remove_readonly)
            os.makedirs(self.run_scripts_dir, exist_ok=True)

    def handle_first_ever_run(self):
        """nukes previously installed dependencies and .bat/.sh scripts for the first ever run of
        the electrumsv-sdk."""
        try:
            with open(self.electrumsv_sdk_config_path, "r") as f:
                config = json.loads(f.read())
        except FileNotFoundError:
            with open(self.electrumsv_sdk_config_path, "w") as f:
                config = {"is_first_run": True}
                f.write(json.dumps(config, indent=4))

        if config.get("is_first_run") or config.get("is_first_run") is None:
            logger.debug(
                "Running SDK for the first time. please wait for configuration to complete..."
            )
            logger.debug("Purging previous server installations (if any)...")
            self.purge_prev_installs_if_exist()
            with open(self.electrumsv_sdk_config_path, "w") as f:
                config = {"is_first_run": False}
                f.write(json.dumps(config, indent=4))
            logger.debug("Purging completed successfully")

            electrumsv_node.reset()
