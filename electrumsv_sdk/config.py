import json
import logging
import os
import sys
from argparse import Namespace
from pathlib import Path
from typing import List, Optional, Dict, Any

from electrumsv_sdk.constants import NameSpace
from electrumsv_sdk.sdk_types import SelectedComponent

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class ParsedArgs(Namespace):
    namespace: Optional[str] = None
    selected_component: SelectedComponent = ""
    component_args: List[str] = []
    node_args: List[str] = []
    repo: str = ""
    branch: str = ""
    new_flag: bool = False
    gui_flag: bool = False
    background_flag: bool = False
    inline_flag: bool = False
    new_terminal_flag: bool = False
    component_id: str = ""
    cli_extension_args: Dict[str, Any] = {}
    sdk_home_dir: str = ""


class CLIInputs(object):

    """
    There is a 1:1 relationship between this cli_inputs and each activation of the SDK cli tool.
    Will also be instantiated inside of wrappers to the install, start, stop, reset entrypoints
    for use as a python library.
    """

    def __init__(self,
            namespace: Optional[str] = None,
            selected_component: SelectedComponent = "",
            component_args: Optional[List[str]] = None,
            node_args: Optional[List[str]] = None,
            repo: str = "",
            branch: str = "",
            new_flag: bool = False,
            gui_flag: bool = False,
            background_flag: bool = False,
            inline_flag: bool = False,
            new_terminal_flag: bool = False,
            component_id: str = "",
            cli_extension_args: Optional[Dict[str, Any]] = None,
            sdk_home_dir: str = "",

    ):
        # ------------------ CLI INPUT VALUES ------------------ #
        self.namespace = namespace
        self.selected_component = selected_component
        self.component_args = component_args if component_args else []
        self.node_args = node_args if node_args else []
        self.repo = repo
        self.branch = branch
        self.new_flag = new_flag
        self.gui_flag = gui_flag
        self.background_flag = background_flag
        self.inline_flag = inline_flag
        self.new_terminal_flag = new_terminal_flag
        self.component_id = component_id
        self.cli_extension_args = cli_extension_args if cli_extension_args else {}
        self.sdk_home_dir = sdk_home_dir


class Config:
    """Maps to a config.json file and is predominantly concerned with file paths and portability
    of the SDK (or else uses the standard location in the user's home directory)."""

    def __init__(self, cli_inputs: Optional[CLIInputs] = None):
        self.logger = logging.getLogger("config")
        self.cli_inputs = cli_inputs
        # ------------------ FILE PATHS ------------------ #
        # Config file location is always found in the standard location in user home directory
        self.CONFIG_PATH: Path = get_sdk_datadir().joinpath("config.json")

        # Whereas these depend on the location of SDK_HOME_DIR for portability reasons
        self.SDK_HOME_DIR: Optional[Path] = None
        self.REMOTE_REPOS_DIR: Optional[Path] = None
        self.DATADIR: Optional[Path] = None
        self.LOGS_DIR: Optional[Path] = None
        self.PYTHON_LIB_DIR: Optional[Path] = None

        # Three possible plugin locations
        self.BUILTIN_PLUGINS_DIRNAME = 'builtin_components'
        self.USER_PLUGINS_DIRNAME = 'user_plugins'
        self.LOCAL_PLUGINS_DIRNAME = 'electrumsv_sdk_plugins'
        self.BUILTIN_COMPONENTS_DIR: Optional[Path] = None
        self.USER_PLUGINS_DIR: Optional[Path] = None
        self.LOCAL_PLUGINS_DIR: Optional[Path] = None

        if self.cli_inputs and self.cli_inputs.namespace == NameSpace.CONFIG:
            assert self.cli_inputs is not None
            self.update_config_file(self.cli_inputs)

        # set global paths based on state of config.json
        self.set_paths()

        assert self.CONFIG_PATH is not None
        assert self.SDK_HOME_DIR is not None
        assert self.REMOTE_REPOS_DIR is not None
        assert self.DATADIR is not None
        assert self.LOGS_DIR is not None
        assert self.PYTHON_LIB_DIR is not None

    def print_json(self):
        print(f"config json:", flush=True)
        print(json.dumps(self.read_config_json(), indent=4), flush=True)

    def set_paths(self):
        self.SDK_HOME_DIR: Path = self.get_dynamic_datadir()
        self.REMOTE_REPOS_DIR: Path = self.SDK_HOME_DIR.joinpath("remote_repos")
        self.DATADIR: Path = self.SDK_HOME_DIR.joinpath("component_datadirs")
        self.LOGS_DIR: Path = self.SDK_HOME_DIR.joinpath("logs")
        self.PYTHON_LIB_DIR: Path = self.SDK_HOME_DIR.joinpath("python_libs")

        # Three possible plugin locations
        self.BUILTIN_COMPONENTS_DIR: Path = Path(MODULE_DIR).joinpath(self.BUILTIN_PLUGINS_DIRNAME)
        self.USER_PLUGINS_DIR: Path = self.SDK_HOME_DIR.joinpath(self.USER_PLUGINS_DIRNAME)
        self.LOCAL_PLUGINS_DIR: Path = Path(os.getcwd()).joinpath(self.LOCAL_PLUGINS_DIRNAME)
        os.makedirs(self.REMOTE_REPOS_DIR, exist_ok=True)
        os.makedirs(self.PYTHON_LIB_DIR, exist_ok=True)
        os.makedirs(self.DATADIR, exist_ok=True)
        os.makedirs(self.LOGS_DIR, exist_ok=True)
        os.makedirs(self.USER_PLUGINS_DIR, exist_ok=True)

    def update_config_file(self, cli_inputs: CLIInputs) -> None:
        """When switching to portable mode the 'sdk_home_dir' is set to **portable** to avoid
        any confusion. It is automatically set back to the default LOCALAPPDATA location when
        turning off portable mode"""
        config = self.read_config_json()  # Config is always stored at LOCALAPPDATA location
        sdk_home_dir = cli_inputs.sdk_home_dir

        if sdk_home_dir:
            config['sdk_home_dir'] = sdk_home_dir

        config['is_first_run'] = False
        self.write_to_config_json(config)

    def search_for_sdk_home_dir(self) -> Path:
        """In portable mode the SDK searches ascending directories until it finds a directory with
        the name: 'SDK_HOME_DIR'"""

        def get_parent_dir(path: Path):
            return path.parent

        current_dir: Path = Path(os.path.dirname(os.path.abspath(sys.executable)))
        while True:
            directories = os.listdir(current_dir)
            if 'SDK_HOME_DIR' in directories:
                sdk_home_dir = current_dir.joinpath('SDK_HOME_DIR')
                # self.logger.debug(f"found SDK_HOME_DIR at: {sdk_home_dir}")
                return sdk_home_dir

            last_dir = current_dir
            current_dir = get_parent_dir(current_dir)
            if last_dir == current_dir:
                raise FileNotFoundError("SDK_HOME_DIR not found")

    def is_portable_mode(self):
        portable_mode = int(os.environ.get("SDK_PORTABLE_MODE", 0))
        if portable_mode == 1:
            return True

    def get_dynamic_datadir(self) -> Path:
        """Check config.json (which needs to *always* be located in the system home directory at
        initial startup) to see if a local directory has been set for SDK_HOME_DIR

        There is an environment variable: SDK_PORTABLE_MODE=1 which will override everything else
        and trigger an ascending search for a directory containing: 'SDK_HOME_DIR' in the name.
        """
        sdk_home_dir = get_sdk_datadir()
        config = self.read_config_json()
        modified_sdk_home_dir = config.get("sdk_home_dir")

        # The --portable cli option was phased out in v0.0.38 in favour of
        # the env var SDK_PORTABLE_MODE=1 for its simpler implementation
        if modified_sdk_home_dir == "**portable**":
            modified_sdk_home_dir = None
            config['sdk_home_dir'] = str(sdk_home_dir)
            if 'portable' in config:
                del config['portable']
            self.write_to_config_json(config)

        # Searches ascending directories for 'SDK_HOME_DIR'
        if self.is_portable_mode():
            if os.environ.get('SDK_HOME_DIR'):
                sdk_home_dir = Path(os.environ['SDK_HOME_DIR'])
            else:
                sdk_home_dir = self.search_for_sdk_home_dir()

        # Pull persisted sdk_home_dir value from config.json for usage
        elif modified_sdk_home_dir is not None:
            sdk_home_dir = Path(modified_sdk_home_dir)

        return sdk_home_dir

    def read_config_json(self) -> Dict:
        assert self.CONFIG_PATH is not None
        if self.CONFIG_PATH.exists():
            with open(self.CONFIG_PATH, "r") as f:
                data = f.read()
                if data.strip():
                    config = json.loads(data)
                else:
                    config = {}

            return config
        else:
            os.makedirs(os.path.dirname(os.path.abspath(self.CONFIG_PATH)))
            with open(self.CONFIG_PATH, "w") as f:
                config = {"is_first_run": False}
                f.write(json.dumps(config, indent=4))
            return {}

    def write_to_config_json(self, config: Dict) -> None:
        assert self.CONFIG_PATH is not None
        with open(self.CONFIG_PATH, 'w') as f:
            f.write(json.dumps(config))
        self.logger.debug(f"updated config.json file at: {self.CONFIG_PATH} with: {config}")


def get_sdk_datadir() -> Path:
    sdk_home_datadir = None
    if sys.platform == "win32":
        sdk_home_datadir = Path(os.environ["LOCALAPPDATA"]) / "ElectrumSV-SDK"
    if sdk_home_datadir is None:
        sdk_home_datadir = Path.home() / ".electrumsv-sdk"
    return sdk_home_datadir
