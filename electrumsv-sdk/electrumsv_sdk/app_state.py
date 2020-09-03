import argparse
import json
import logging
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Dict, List, Set

from electrumsv_node import electrumsv_node

from .constants import DEFAULT_ID_ELECTRUMSV, DEFAULT_PORT_ELECTRUMSV
from .argparsing import ArgParser
from .components import ComponentName
from .controller import Controller
from .handlers import Handlers
from .install_tools import InstallTools
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

        self.arparser = ArgParser(self)
        self.controller = Controller(self)
        self.handlers = Handlers(self)
        self.install_tools = InstallTools(self)
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

        # electrumsv paths are set dynamically at startup - see: set_electrumsv_path()
        self.electrumsv_dir = None
        self.electrumsv_data_dir = None
        self.electrumsv_regtest_dir = None
        self.electrumsv_regtest_config_path = None
        self.electrumsv_regtest_wallets_dir = None
        self.electrumsv_requirements_path = None
        self.electrumsv_binary_requirements_path = None

        self.electrumx_dir = self.depends_dir.joinpath("electrumx")
        self.electrumx_data_dir = self.depends_dir.joinpath("electrumx_data")

        self.sdk_package_dir = Path(MODULE_DIR)
        self.status_monitor_dir = self.sdk_package_dir.joinpath("status_server")

        self.start_set: Set[ComponentName] = set()
        self.start_options: Dict[ComponentName] = {}
        self.stop_set: Set[ComponentName] = set()

        self.node_args = None

    def set_electrumsv_path(self, electrumsv_dir: Path):
        """This is set dynamically at startup. It is *only persisted for purposes of the 'reset'
        command. The trade-off is that the electrumsv 'repo' will need to be specified anew every
        time the SDK 'start' command is run."""
        self.electrumsv_dir = electrumsv_dir
        self.update_electrumsv_data_dir(self.electrumsv_dir.joinpath(DEFAULT_ID_ELECTRUMSV),
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
                self.set_electrumsv_path(Path(electrumsv_dir))
            else:
                self.set_electrumsv_path(Path(self.depends_dir.joinpath("electrumsv")))

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
        """nukes previously installed dependencies and .bat/.sh scripts for the first ever run of the
        electrumsv-sdk."""
        try:
            with open(self.electrumsv_sdk_config_path, "r") as f:
                config = json.loads(f.read())
        except FileNotFoundError:
            with open(self.electrumsv_sdk_config_path, "w") as f:
                config = {"is_first_run": True}
                f.write(json.dumps(config, indent=4))

        if config.get("is_first_run") or config.get("is_first_run") is None:
            logger.debug(
                "running SDK for the first time. please wait for configuration to complete..."
            )
            logger.debug("purging previous server installations (if any)...")
            self.purge_prev_installs_if_exist()
            with open(self.electrumsv_sdk_config_path, "w") as f:
                config = {"is_first_run": False}
                f.write(json.dumps(config, indent=4))
            logger.debug("purging completed successfully")

            electrumsv_node.reset()
