import json
import logging
import os
import sys
from argparse import Namespace
from pathlib import Path
from typing import List, Optional, Dict, Any

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
    portable: str = "str"


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
            portable: str = ""

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
        self.portable = portable


class Config:
    """Maps to a cli_inputs.json file and is predominantly concerned with file paths and portability
    of the SDK (or else uses the standard location in the user's home directory)."""

    def __init__(self, cli_inputs: Optional[CLIInputs] = None):
        self.logger = logging.getLogger("config")
        self.cli_inputs = cli_inputs
        # ------------------ FILE PATHS ------------------ #
        self.CONFIG_PATH: Optional[Path] = None
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

        self.set_paths()
        if self.cli_inputs:
            self.update_config_file(cli_inputs)
            self.set_paths()  # called again because values will likely be different now

    def print_json(self):
        print(f"config json:")
        print(json.dumps(read_config_json(self), indent=4))

    def set_paths(self):
        # Config file location is always found in the standard location in user home directory
        self.CONFIG_PATH: Path = get_sdk_datadir().joinpath("cli_inputs.json")

        # Whereas these depend on the location of SDK_HOME_DIR for portability reasons
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

    def update_config_file(self, cli_inputs) -> None:
        """When switching to portable mode the 'sdk_home_dir' is set to **portable** to avoid
        any confusion. It is automatically set back to the default LOCALAPPDATA location when
        turning off portable mode"""
        config = read_config_json(self)  # Config is always stored at LOCALAPPDATA location
        sdk_home_dir = cli_inputs.sdk_home_dir
        portable_mode = cli_inputs.portable

        # Both options cannot coexist
        if sdk_home_dir and portable_mode is True:
            return

        if sdk_home_dir:
            config['sdk_home_dir'] = self.SDK_HOME_DIR

        elif portable_mode:
            config['sdk_home_dir'] = "**portable**"
            config['portable'] = portable_mode

        # When switching off portable mode need to replace '**portable**' with default LOCALAPPDATA
        # Location for the SDK_HOME_DIR
        elif portable_mode is False:
            config['portable'] = False
            if config.get('sdk_home_dir', '') in {"**portable**", ""}:
                config['sdk_home_dir'] = str(get_sdk_datadir())

        write_to_config_json(config)

    def get_dynamic_datadir(self) -> Path:
        """Check config.json (which needs to *always* be located in the system home directory at
        initial startup) to see if a local directory has been set for SDK_HOME_DIR (or if it is
        set to 'portable' mode"""

        # Todo - if --portable mode is true then search ascending directories
        def is_portable_mode(config: Dict):
            if self.cli_inputs is not None and self.cli_inputs.portable is True:
                return True

            portable_mode = config.get('portable', False)
            if portable_mode:
                return portable_mode

        sdk_home_dir = get_sdk_datadir()
        config = read_config_json(self)
        modified_sdk_home_dir = config.get("sdk_home_dir")

        if is_portable_mode(config):
            # Todo - if --portable mode is true then search ascending directories
            self.logger.warning(f"portability mode feature not fully implemented yet")

        # Reset to default sdk_home_dir (on switching portable mode off)
        if modified_sdk_home_dir == "**portable**" and not is_portable_mode(config):
            sdk_home_dir = get_sdk_datadir()

        # Pull persisted sdk_home_dir value from config.json for usage
        elif modified_sdk_home_dir is not None and modified_sdk_home_dir != "**portable**":
            sdk_home_dir = Path(modified_sdk_home_dir)
        return sdk_home_dir


def read_config_json(config: Config) -> Dict:
    CONFIG_PATH = config.CONFIG_PATH
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            data = f.read()
            if data.strip():
                config = json.loads(data)
            else:
                config = {}

        return config
    else:
        return {}



def write_to_config_json(config: Dict) -> None:
    config_file_json = Config()
    with open(config_file_json.CONFIG_PATH, 'w') as f:
        f.write(json.dumps(config))



def get_sdk_datadir() -> Path:
    sdk_home_datadir = None
    if sys.platform == "win32":
        sdk_home_datadir = Path(os.environ["LOCALAPPDATA"]) / "ElectrumSV-SDK"
    if sdk_home_datadir is None:
        sdk_home_datadir = Path.home() / ".electrumsv-sdk"
    return sdk_home_datadir
