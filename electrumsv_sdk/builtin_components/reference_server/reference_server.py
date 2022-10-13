import logging
import os
import sys
from typing import Optional, Set

from electrumsv_sdk.sdk_types import AbstractPlugin
from electrumsv_sdk.config import CLIInputs, Config
from electrumsv_sdk.components import Component
from electrumsv_sdk.utils import is_remote_repo, get_directory_name, kill_process
from electrumsv_sdk.plugin_tools import PluginTools

from .local_tools import LocalTools


class Plugin(AbstractPlugin):

    DEFAULT_PORT = 47124
    RESERVED_PORTS: Set[int] = {DEFAULT_PORT}
    COMPONENT_NAME = get_directory_name(__file__)
    DEFAULT_REMOTE_REPO = "https://github.com/electrumsv/electrumsv-reference-server"

    REFERENCE_SERVER_RESET = os.environ.get("REFERENCE_SERVER_RESET", '0')
    EXPOSE_HEADER_SV_APIS = os.environ.get("EXPOSE_HEADER_SV_APIS", '1')
    HEADER_SV_URL = os.environ.get("HEADER_SV_URL", 'http://127.0.0.1:33444')

    def __init__(self, cli_inputs: CLIInputs) -> None:
        self.cli_inputs = cli_inputs
        self.config = Config()
        self.plugin_tools = PluginTools(self, self.cli_inputs)
        self.tools = LocalTools(self)
        self.logger = logging.getLogger(self.COMPONENT_NAME)

        self.src = self.plugin_tools.get_source_dir(dirname="electrumsv-reference-server")
        self.datadir = None  # dynamically allocated
        self.id = None  # dynamically allocated
        self.port = None  # dynamically allocated
        self.component_info: Optional[Component] = None

    def install(self) -> None:
        """required state: source_dir  - which are derivable from 'repo' and 'branch' flags"""
        self.plugin_tools.modify_pythonpath_for_portability(self.src)

        repo = self.cli_inputs.repo
        if self.cli_inputs.repo == "":
            repo = self.DEFAULT_REMOTE_REPO
        if is_remote_repo(repo):
            self.tools.fetch_reference_server(repo, self.cli_inputs.branch)

        self.tools.packages_reference_server(repo, self.cli_inputs.branch)

    def start(self) -> None:
        """plugin datadir, id, port are allocated dynamically"""
        self.logger.debug("Starting RegTest reference_server daemon...")
        assert self.src is not None  # typing bug
        if not self.src.exists():
            self.logger.error("source code directory does not exist - try 'electrumsv-sdk install "
                              "%s' to install the plugin first", self.COMPONENT_NAME)
            sys.exit(1)

        self.plugin_tools.modify_pythonpath_for_portability(self.src)
        self.datadir, self.id = self.plugin_tools.allocate_datadir_and_id()
        self.port = self.plugin_tools.allocate_port()

        command = f"{sys.executable} {self.src.joinpath('server.py')}"
        env_vars = {
            "PYTHONUNBUFFERED": "1",
            "REFERENCE_SERVER_RESET": self.REFERENCE_SERVER_RESET,
            "EXPOSE_HEADER_SV_APIS": self.EXPOSE_HEADER_SV_APIS,
            "HEADER_SV_URL": self.HEADER_SV_URL
        }
        logfile = self.plugin_tools.get_logfile_path(self.id)
        self.plugin_tools.spawn_process(command, env_vars=env_vars, id=self.id,
            component_name=self.COMPONENT_NAME, src=self.src, logfile=logfile,
            status_endpoint=f"http://127.0.0.1:{self.port}",
            metadata={"datadir": str(self.datadir)})

    def stop(self) -> None:
        """some components require graceful shutdown via a REST API or RPC API but most can use the
        generic 'app_state.kill_component()' function to track down the pid and kill the process."""
        self.plugin_tools.call_for_component_id_or_type(self.COMPONENT_NAME, callable=kill_process)
        self.logger.info("stopped selected %s instance (if running)", self.COMPONENT_NAME)

    def reset(self) -> None:
        self.stop()
        self.logger.debug("Resetting state of RegTest reference_server...")

        assert self.src is not None
        for filename in { "esv_reference_server.sqlite" }:
            filepath = self.src.joinpath(filename)
            if filepath.exists():
                os.remove(filepath)

        self.logger.info("Reset of RegTest reference_server completed successfully")
