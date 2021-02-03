import logging
import os
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Dict

from electrumsv_sdk.abstract_plugin import AbstractPlugin
from electrumsv_sdk.config import Config
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import get_directory_name
from electrumsv_sdk.plugin_tools import PluginTools

from electrumsv_node import electrumsv_node

from .local_tools import LocalTools


def extend_start_cli(start_parser: ArgumentParser):
    """if this method is present it allows extension of the start argparser only.
    This occurs dynamically and adds the new cli options as attributes of the Config object"""
    start_parser.add_argument("--regtest", action="store_true", help="run on regtest")
    start_parser.add_argument("--testnet", action="store_true", help="run on testnet")

    # variable names to be pulled from the start_parser
    new_options = ['regtest', 'testnet']
    return start_parser, new_options


class Plugin(AbstractPlugin):

    BITCOIN_NETWORK = os.getenv("BITCOIN_NETWORK", "regtest")

    # if ports == None -> set by deterministic port allocation
    NODE_PORT = os.environ.get("NODE_PORT")
    NODE_P2P_PORT = os.environ.get("NODE_P2P_PORT")
    NODE_ZMQ_PORT = os.environ.get("NODE_ZMQ_PORT")

    NODE_RPCALLOWIP = os.environ.get("NODE_RPCALLOWIP")  # else 127.0.0.1
    NODE_RPCBIND = os.environ.get("NODE_RPCBIND")

    DEFAULT_PORT = 18332
    DEFAULT_P2P_PORT = 18444
    DEFAULT_ZMQ_PORT = 28332
    RESERVED_PORTS = {DEFAULT_PORT, DEFAULT_P2P_PORT}
    COMPONENT_NAME = get_directory_name(__file__)

    def __init__(self, config: Config):
        self.config = config
        self.plugin_tools = PluginTools(self, self.config)
        self.tools = LocalTools(self)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = Path(electrumsv_node.FILE_PATH).parent
        self.datadir = None  # dynamically allocated
        self.id = None  # dynamically allocated
        self.port = None  # dynamically allocated
        self.p2p_port = None  # dynamically allocated
        self.zmq_port = None  # dynamically allocated
        self.component_info: Optional[Component] = None

        self.network = self.BITCOIN_NETWORK

    def install(self):
        """The node component has a pip installer at https://pypi.org/project/electrumsv-node/ and
        only official releases from pypi are supported"""
        self.tools.fetch_node()
        self.logger.debug(f"Installed {self.COMPONENT_NAME}")

    def start(self):
        # env vars take precedence for port and dbdir
        self.datadir, self.id = self.plugin_tools.allocate_datadir_and_id()
        self.tools.process_cli_args()  # cli args may override network in env vars

        if self.NODE_PORT:
            self.port = self.NODE_PORT
        else:
            self.port = self.plugin_tools.allocate_port()

        if self.NODE_P2P_PORT:
            self.p2p_port = self.NODE_P2P_PORT
        else:
            self.p2p_port = self.plugin_tools.get_component_port(self.DEFAULT_P2P_PORT,
                self.COMPONENT_NAME, self.id)

        if self.NODE_ZMQ_PORT:
            self.zmq_port = self.NODE_ZMQ_PORT
        else:
            self.zmq_port = self.plugin_tools.get_component_port(self.DEFAULT_ZMQ_PORT,
                self.COMPONENT_NAME, self.id)

        extra_params = []
        if self.NODE_RPCALLOWIP:
            extra_params.append(f"-rpcallowip={self.NODE_RPCALLOWIP}")
        if self.NODE_RPCBIND:
            extra_params.append(f"-rpcbind={self.NODE_RPCBIND}")
        if not extra_params:
            extra_params = None

        shell_command = electrumsv_node.shell_command(data_path=str(self.datadir),
            rpcport=self.port, p2p_port=self.p2p_port, zmq_port=self.zmq_port, network=self.network,
            print_to_console=True, extra_params=extra_params)

        command = " ".join(shell_command)
        logfile = self.plugin_tools.get_logfile_path(self.id)
        self.plugin_tools.spawn_process(command, env_vars=None, id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            status_endpoint=f"http://rpcuser:rpcpassword@127.0.0.1:{self.port}",
            metadata={"DATADIR": str(self.datadir), "rpcport": self.port, "p2p_port": self.p2p_port}
        )
        if electrumsv_node.is_node_running():
            return
        else:
            self.logger.exception("node failed to start")

    def stop(self):
        """The bitcoin node requires graceful shutdown via the RPC API - a good example of why this
        entrypoint is provided for user customizations (rather than always killing the process)."""
        def stop_node(component_dict: Dict):
            rpcport = component_dict.get("metadata").get("rpcport")
            if not rpcport:
                raise Exception("rpcport data not found")
            electrumsv_node.stop(rpcport=rpcport)

        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=stop_node)
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance (if running)")

    def reset(self):
        def reset_node(component_dict: Dict):
            rpcport = component_dict.get("metadata").get("rpcport")
            datadir = component_dict.get("metadata").get("DATADIR")
            if not rpcport:
                raise Exception("rpcport data not found")
            electrumsv_node.reset(data_path=datadir, rpcport=rpcport)

        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=reset_node)
        self.logger.info("Reset of RegTest bitcoin daemon completed successfully.")
