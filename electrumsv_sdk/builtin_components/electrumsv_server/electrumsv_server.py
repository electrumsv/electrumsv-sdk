import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Tuple, List, Set
import shutil

from electrumsv_sdk.sdk_types import AbstractPlugin
from electrumsv_sdk.config import Config
from electrumsv_sdk.components import Component, ComponentTypedDict
from electrumsv_sdk.utils import get_directory_name, kill_process
from electrumsv_sdk.plugin_tools import PluginTools

from .local_tools import LocalTools


MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


def extend_start_cli(start_parser: ArgumentParser) -> Tuple[ArgumentParser, List[str]]:
    """if this method is present it allows extension of the start argparser only.
    This occurs dynamically and adds the new cli options as attributes of the Config object"""
    start_parser.add_argument("--mapi-broadcast", action="store_true",
        help="turn on broadcasting via the merchant api")
    start_parser.add_argument("--mapi-host", type=str, default="127.0.0.1",
        help="merchant api host")
    start_parser.add_argument("--mapi-port", type=int, default=5051,
        help="merchant api port")

    start_parser.add_argument("--regtest", action="store_true", help="run on regtest")
    start_parser.add_argument("--testnet", action="store_true", help="run on testnet")
    start_parser.add_argument("--scaling-testnet", action="store_true",
        help="run on scaling-testnet")
    start_parser.add_argument("--main", action="store_true", help="run on mainnet")

    # variable names to be pulled from the start_parser
    new_options = ['mapi_broadcast', "mapi_host", "mapi_port", "regtest", "scaling_testnet",
        "testnet", "main"]
    return start_parser, new_options


class Plugin(AbstractPlugin):
    SERVER_HOST = "127.0.0.1"
    SERVER_PORT = 24242
    RESERVED_PORTS: Set[int] = {SERVER_PORT}

    COMPONENT_NAME = get_directory_name(__file__)
    COMPONENT_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
    ELECTRUMSV_SERVER_MODULE_PATH = Path(MODULE_DIR).parent.parent.parent.joinpath(
        "electrumsv-server")

    def __init__(self, config: Config) -> None:
        self.config = config
        self.plugin_tools = PluginTools(self, self.config)
        self.tools = LocalTools(self)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.COMPONENT_PATH
        self.datadir = None  # dynamically allocated
        self.id = None  # dynamically allocated
        self.port = None  # dynamically allocated
        self.component_info: Optional[Component] = None

    def install(self) -> None:
        self.logger.debug(f"Installing {self.COMPONENT_NAME} is not applicable")

    def start(self) -> None:
        self.datadir, self.id = self.plugin_tools.get_component_datadir(self.COMPONENT_NAME)
        logfile = self.plugin_tools.get_logfile_path(self.id)
        env_vars = {"PYTHONUNBUFFERED": "1"}
        os.makedirs(self.ELECTRUMSV_SERVER_MODULE_PATH.joinpath("data"), exist_ok=True)
        os.chdir(self.ELECTRUMSV_SERVER_MODULE_PATH)
        command = f"{sys.executable} -m electrumsv_server --wwwroot-path=wwwroot " \
            f"--data-path={self.datadir} "

        network_choice = self.tools.get_network_choice()
        command += f"--{network_choice}"

        # These mapi attributes are added to config as extension cli options
        # (see: extend_start_cli() above)
        if self.config.cli_extension_args['mapi_broadcast']:
            command += (f" --mapi-broadcast "
                        f"--mapi-host={self.config.cli_extension_args['mapi_host']} "
                        f"--mapi-port={self.config.cli_extension_args['mapi_port']}")

        self.plugin_tools.spawn_process(command, env_vars=env_vars, id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            metadata={"datadir": str(self.datadir)})

    def stop(self) -> None:
        self.logger.debug("Attempting to kill the process if it is even running")
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)

    def reset(self) -> None:
        def reset_server(component_dict: ComponentTypedDict) -> None:
            metadata = component_dict.get("metadata", {})
            assert metadata is not None  # typing bug
            datadir: Path = Path(metadata["datadir"])
            if datadir.exists():
                shutil.rmtree(datadir)
                os.mkdir(datadir)
            else:
                os.makedirs(datadir, exist_ok=True)

        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=reset_server)
        self.logger.info(f"Reset of {self.COMPONENT_NAME} completed successfully.")
