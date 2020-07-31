import argparse
import shutil
import stat
from pathlib import Path
from typing import Dict, List, Set
from os.path import expanduser
import json
import logging
import os

from electrumsv_node import electrumsv_node
from electrumsv_sdk.argparsing import ArgParser
from electrumsv_sdk.components import Component, ComponentName
from electrumsv_sdk.install_handlers import InstallHandlers
from electrumsv_sdk.install_tools import InstallTools
from electrumsv_sdk.reset import Resetters
from electrumsv_sdk.runners import Runners
from electrumsv_sdk.status_monitor_client import StatusMonitorClient
from electrumsv_sdk.utils import create_if_not_exist
from filelock import FileLock

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger("status")
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)


class AppState:
    """Only electrumsv paths are saved to config.json so that 'reset' works on correct wallet."""

    def __init__(self):
        self.arparser = ArgParser(self)
        self.install_handlers = InstallHandlers(self)
        self.runners = Runners(self)
        self.install_tools = InstallTools(self)
        self.resetters = Resetters(self)
        self.status_monitor_client = StatusMonitorClient(self)

        # component state
        self.file_path = "component_state.json"
        self.lock_path = "component_state.json.lock"

        self.file_lock = FileLock(self.lock_path, timeout=1)
        self.status: List[Component] = []
        self.component_state_path = Path(MODULE_DIR).joinpath("component_state.json")

        # namespaces
        self.NAMESPACE = ""  # 'start', 'stop' or 'reset'

        self.TOP_LEVEL = "top_level"
        self.START = "start"
        self.STOP = "stop"
        self.RESET = "reset"
        self.NODE = "node"
        self.STATUS = "status"

        # package names
        self.ELECTRUMSV = ComponentName.ELECTRUMSV
        self.ELECTRUMX = ComponentName.ELECTRUMX
        self.ELECTRUMSV_INDEXER = ComponentName.INDEXER
        self.ELECTRUMSV_NODE = ComponentName.NODE
        self.STATUS_MONITOR = ComponentName.STATUS_MONITOR

        self.subcmd_map: Dict[str, argparse.ArgumentParser] = {}  # cmd_name: ArgumentParser
        self.subcmd_raw_args_map: Dict[str, List[str]] = {}  # cmd_name: raw arguments
        self.subcmd_parsed_args_map = {}  # cmd_name: parsed arguments

        self.sdk_requirements_linux = (
            Path(MODULE_DIR).parent.joinpath("requirements").joinpath("requirements-linux.txt")
        )
        self.sdk_requirements_win32 = (
            Path(MODULE_DIR).parent.joinpath("requirements").joinpath("requirements-win32.txt")
        )

        # exclude plyvel from electrumx requirements.txt (windows workaround)
        self.sdk_requirements_electrumx = (
            Path(MODULE_DIR).parent.joinpath("requirements").joinpath("requirements-electrumx.txt")
        )

        self.sdk_package_dir = Path(MODULE_DIR)
        self.electrumsv_sdk_config_path = self.sdk_package_dir.joinpath("config.json")

        self.home = Path(expanduser("~"))
        self.electrumsv_sdk_data_dir = self.home.joinpath("ElectrumSV-SDK")
        self.depends_dir = self.electrumsv_sdk_data_dir.joinpath("sdk_depends")
        self.run_scripts_dir = self.electrumsv_sdk_data_dir.joinpath("run_scripts")
        self.proc_ids_path = self.run_scripts_dir.joinpath("proc_ids.json")

        # electrumsv paths are set dynamically at startup - see: set_electrumsv_path()
        self.electrumsv_dir = None
        self.electrumsv_data_dir = None
        self.electrumsv_regtest_dir = None
        self.electrumsv_regtest_config_dir = None
        self.electrumsv_regtest_wallets_dir = None
        self.electrumsv_requirements_path = None
        self.electrumsv_binary_requirements_path = None

        self.electrumx_dir = self.depends_dir.joinpath("electrumx")
        self.electrumx_data_dir = self.depends_dir.joinpath("electrumx_data")

        self.status_monitor_dir = self.sdk_package_dir.joinpath("status_server")

        self.required_dependencies_set: Set[str] = set()

        self.node_args = None

    def set_electrumsv_path(self, electrumsv_dir: Path):
        """This is set dynamically at startup. It is *only persisted for purposes of the 'reset'
        command. The trade-off is that the electrumsv 'repo' will need to be specified anew every
        time the SDK 'start' command is run."""
        self.electrumsv_dir = electrumsv_dir
        self.electrumsv_data_dir = self.electrumsv_dir.joinpath("electrum_sv_data")
        self.electrumsv_regtest_dir = self.electrumsv_data_dir.joinpath("regtest")
        self.electrumsv_regtest_config_dir = self.electrumsv_regtest_dir.joinpath("config")
        self.electrumsv_regtest_wallets_dir = self.electrumsv_regtest_dir.joinpath("wallets")
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

    def save_repo_paths(self):
        """overwrites config.json"""
        config_path = self.electrumsv_sdk_config_path
        with open(config_path.__str__(), "r") as f:
            config = json.loads(f.read())

        with open(config_path.__str__(), "w") as f:
            config["electrumsv_dir"] = self.electrumsv_dir.__str__()
            f.write(json.dumps(config, indent=4))

    def load_repo_paths(self) -> "self":
        """loads state from config.json"""
        config_path = self.electrumsv_sdk_config_path
        with open(config_path.__str__(), "r") as f:
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
            shutil.rmtree(self.depends_dir.__str__(), onerror=remove_readonly)
            create_if_not_exist(self.depends_dir.__str__())
        if self.run_scripts_dir.exists():
            shutil.rmtree(self.run_scripts_dir.__str__(), onerror=remove_readonly)
            create_if_not_exist(self.run_scripts_dir.__str__())

    def handle_first_ever_run(self):
        """nukes previously installed dependencies and .bat/.sh scripts for the first ever run of the
        electrumsv-sdk."""
        try:
            with open(self.electrumsv_sdk_config_path.__str__(), "r") as f:
                config = json.loads(f.read())
        except FileNotFoundError:
            with open(self.electrumsv_sdk_config_path.__str__(), "w") as f:
                config = {"is_first_run": True}
                f.write(json.dumps(config, indent=4))

        if config.get("is_first_run") or config.get("is_first_run") is None:
            logger.debug(
                "running SDK for the first time. please wait for configuration to complete..."
            )
            logger.debug("purging previous server installations (if any)...")
            self.purge_prev_installs_if_exist()
            with open(self.electrumsv_sdk_config_path.__str__(), "w") as f:
                config = {"is_first_run": False}
                f.write(json.dumps(config, indent=4))
            logger.debug("purging completed successfully")

            electrumsv_node.reset()

    def get_status(self, component_state_path):
        filelock_logger = logging.getLogger("filelock")
        filelock_logger.setLevel(logging.WARNING)

        with self.file_lock:
            with open(component_state_path, "r") as f:
                component_state = json.loads(f.read())

        logger.debug(component_state)

    def find_component_if_exists(self, component: Component, component_state: List[dict]):
        for index, comp in enumerate(component_state):
            if comp["process_name"] == component.process_name:
                return (index, component)
        return False


    def update_status_file(self, component_state_path, component):
        """updates to the *file* (component.json) - does *not* update the server"""

        with self.file_lock:
            with open(component_state_path, "r") as f:
                data = f.read()
                if not data:
                    component_state = []  # assume file was empty
                else:
                    component_state = json.loads(data)

        result = self.find_component_if_exists(component, component_state)
        if not result:
            component_state.append(component.to_dict())
        else:
            index, component = result
            component_state[index] = component.to_dict()

        with open(component_state_path, "w") as f:
            f.write(json.dumps(component_state, indent=4))
