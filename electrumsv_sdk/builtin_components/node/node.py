import logging
import os
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Tuple, List, Set

from electrumsv_sdk.sdk_types import AbstractPlugin
from electrumsv_sdk.config import Config
from electrumsv_sdk.components import Component, ComponentTypedDict, ComponentMetadata
from electrumsv_sdk.utils import get_directory_name
from electrumsv_sdk.plugin_tools import PluginTools

from electrumsv_node import electrumsv_node

from .local_tools import LocalTools


def extend_start_cli(start_parser: ArgumentParser) -> Tuple[ArgumentParser, List[str]]:
    """if this method is present it allows extension of the start argparser only.
    This occurs dynamically and adds the new cli options as attributes of the Config object"""
    start_parser.add_argument("--regtest", action="store_true", help="run on regtest")
    start_parser.add_argument("--testnet", action="store_true", help="run on testnet")

    # variable names to be pulled from the start_parser
    new_options = ['regtest', 'testnet']
    return start_parser, new_options


class Plugin(AbstractPlugin):

    BITCOIN_NETWORK = os.getenv("BITCOIN_NETWORK", "regtest")

    DEFAULT_PORT = 18332
    DEFAULT_P2P_PORT = 18444
    DEFAULT_ZMQ_PORT = 28332

    # if ports == None -> set by deterministic port allocation
    NODE_PORT: int = int(os.environ.get("NODE_PORT") or DEFAULT_PORT)
    NODE_P2P_PORT: int = int(os.environ.get("NODE_P2P_PORT") or DEFAULT_P2P_PORT)
    NODE_ZMQ_PORT: int = int(os.environ.get("NODE_ZMQ_PORT") or DEFAULT_ZMQ_PORT)

    NODE_RPCALLOWIP = os.environ.get("NODE_RPCALLOWIP")  # else 127.0.0.1
    NODE_RPCBIND = os.environ.get("NODE_RPCBIND")

    RESERVED_PORTS: Set[int] = {DEFAULT_PORT, DEFAULT_P2P_PORT}
    COMPONENT_NAME = get_directory_name(__file__)

    def __init__(self, config: Config):
        self.config = config
        self.plugin_tools = PluginTools(self, self.config)
        self.tools = LocalTools(self)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = Path(electrumsv_node.FILE_PATH).parent
        self.datadir: Optional[Path] = None  # dynamically allocated
        self.id: Optional[str] = None  # dynamically allocated
        self.port: Optional[int] = None  # dynamically allocated
        self.p2p_port: Optional[int] = None  # dynamically allocated
        self.zmq_port: Optional[int] = None  # dynamically allocated
        self.component_info: Optional[Component] = None

        self.network = self.BITCOIN_NETWORK

    def install(self) -> None:
        """The node component has a pip installer at https://pypi.org/project/electrumsv-node/ and
        only official releases from pypi are supported"""
        self.plugin_tools.modify_pythonpath_for_portability(self.src)

        self.tools.fetch_node()
        self.logger.debug(f"Installed {self.COMPONENT_NAME}")

    def start(self) -> None:
        self.plugin_tools.modify_pythonpath_for_portability(self.src)

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

        shell_command = electrumsv_node.shell_command(data_path=str(self.datadir),
            rpcport=self.port, p2p_port=self.p2p_port, zmq_port=self.zmq_port, network=self.network,
            print_to_console=True, extra_params=extra_params)

        command = " ".join(shell_command)
        logfile = self.plugin_tools.get_logfile_path(self.id)
        self.plugin_tools.spawn_process(command, env_vars=os.environ.copy(), id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            status_endpoint=f"http://rpcuser:rpcpassword@127.0.0.1:{self.port}",
            metadata=ComponentMetadata(
                datadir=str(self.datadir),
                rpcport=self.port,
                p2p_port=self.p2p_port
            )
        )
        if electrumsv_node.is_node_running():
            return
        else:
            self.logger.exception("node failed to start")

    def stop(self) -> None:
        """The bitcoin node requires graceful shutdown via the RPC API - a good example of why this
        entrypoint is provided for user customizations (rather than always killing the process)."""
        def stop_node(component_dict: ComponentTypedDict) -> None:
            metadata = component_dict.get("metadata", {})
            assert metadata is not None  # typing bug
            rpcport = metadata.get("rpcport")
            if not rpcport:
                raise Exception("rpcport data not found")
            electrumsv_node.stop(rpcport=rpcport)

        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=stop_node)
        self.logger.info(f"stopped selected {self.COMPONENT_NAME} instance (if running)")

    def reset(self) -> None:
        def reset_node(component_dict: ComponentTypedDict) -> None:
            metadata = component_dict.get("metadata", {})
            assert metadata is not None  # typing bug
            rpcport = metadata.get('rpcport')
            datadir = metadata.get("datadir")
            if not rpcport:
                raise Exception("rpcport data not found")
            electrumsv_node.reset(data_path=datadir, rpcport=rpcport)

        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=reset_node)
        self.logger.info("Reset of RegTest bitcoin daemon completed successfully.")
