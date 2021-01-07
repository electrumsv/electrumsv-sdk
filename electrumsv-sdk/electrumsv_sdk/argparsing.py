"""
As a workaround to lack of support for argparse to take multiple subcommands (+/- args)
simultaneously sys.argv is manually parsed to find the relevant args to feed to the appropriate
ArgumentParser instance.

Fortunately the help menu displays as expected so does not deviate from the standard docuementation.
"""

import argparse
import logging
import sys
from typing import Optional, Dict, List

from .constants import NameSpace
from .config import Config
from .validate_cli_args import ValidateCliArgs
from .components import ComponentStore

logger = logging.getLogger("argparsing")


class ArgParser:
    def __init__(self):
        self.component_store = ComponentStore()

        # globals that are packed into Config after argparsing
        self.namespace: Optional[str] = ""  # 'start', 'stop', 'reset', 'node', or 'status'
        self.selected_component: Optional[str] = None
        self.component_args = []  # e.g. store arguments to pass to the electrumsv's cli interface
        self.node_args = None

        # data types for storing intermediate steps of argparsing
        self.parser_map: Dict[str, argparse.ArgumentParser] = {}  # namespace: ArgumentParser
        self.parser_raw_args_map: Dict[str, List[str]] = {}  # {namespace: raw arguments}
        self.subcmd_parsed_args_map = {}  # {namespace: parsed arguments}
        self.config = None

        self.new_options = None  # used for dynamic, plugin-specific extensions to cli
        self.setup_argparser()

    def validate_cli_args(self):
        """calls the appropriate handler for the argparsing.NameSpace"""
        handler = ValidateCliArgs(self.config)
        parsed_args = self.subcmd_parsed_args_map[self.config.namespace]
        func = getattr(handler, "handle_" + self.config.namespace + "_args")
        func(parsed_args)

    def parse_first_arg(self, arg, cur_cmd_name, subcommand_indices):
        if arg in {NameSpace.INSTALL, NameSpace.START, NameSpace.STOP, NameSpace.RESET,
                NameSpace.NODE, NameSpace.STATUS}:
            cur_cmd_name = arg
            self.namespace = arg
            subcommand_indices[arg] = []
        elif arg == "--help":
            subcommand_indices[NameSpace.TOP_LEVEL].append(0)
        elif arg == "--version":
            subcommand_indices[NameSpace.TOP_LEVEL].append(0)
        else:
            logger.error("First argument must be one of: "
                "[start, stop, reset, node, status, --help, --version]")
            sys.exit(1)
        return cur_cmd_name, subcommand_indices

    def manual_argparsing(self, args: List[str]) -> Config:
        """manually iterate through sys.argv and feed arguments to either:
        a) parent ArgumentParser
        b) child ArgumentParsers (aka subcommands)"""
        component_selected = False
        args.pop(0)

        subcommand_indices = {}  # cmd_name: [index_arg1, index_arg2]

        cur_cmd_name = NameSpace.TOP_LEVEL
        self.namespace = NameSpace.TOP_LEVEL
        subcommand_indices[NameSpace.TOP_LEVEL] = []
        for index, arg in enumerate(args):
            if index == 0:
                cur_cmd_name, subcommand_indices = self.parse_first_arg(
                    arg, cur_cmd_name, subcommand_indices
                )
                continue

            elif self.namespace == NameSpace.TOP_LEVEL:
                subcommand_indices[NameSpace].append(index)

            elif self.namespace in {NameSpace.START, NameSpace.INSTALL}:
                # <start options>
                if arg.startswith("--") and not component_selected:
                    subcommand_indices[cur_cmd_name].append(index)
                    continue

                # <component name>
                elif not arg.startswith("-") and not component_selected:
                    cur_cmd_name = arg
                    subcommand_indices[cur_cmd_name] = []
                    if arg in self.component_store.component_map.keys():
                        self.selected_component = arg
                    else:
                        logger.error(f"Must select from: "
                                     f"{self.component_store.component_map.keys()}")
                        sys.exit()
                    component_selected = True
                    continue

                # <arguments to pass to component> (e.g. to standard electrumsv cli interface)
                elif component_selected:
                    self.component_args.append(arg)
                    continue

            elif self.namespace == NameSpace.STOP:
                # <stop options>
                if arg.startswith("--") and not component_selected:
                    subcommand_indices[cur_cmd_name].append(index)
                    continue

                # <component name>
                if not arg.startswith("-") and not component_selected:
                    cur_cmd_name = arg
                    subcommand_indices[cur_cmd_name] = []
                    if arg in self.component_store.component_map.keys():
                        self.selected_component = arg
                    else:
                        logger.error(f"Must select from: "
                                     f"{self.component_store.component_map.keys()}")
                        sys.exit()
                    component_selected = True
                    continue

            elif self.namespace == NameSpace.RESET:
                # <reset options>
                if arg.startswith("--") and not component_selected:
                    subcommand_indices[cur_cmd_name].append(index)
                    continue

                # <component name>
                if not arg.startswith("-") and not component_selected:
                    cur_cmd_name = arg
                    subcommand_indices[cur_cmd_name] = []
                    if arg in self.component_store.component_map.keys():
                        self.selected_component = arg
                    else:
                        logger.error(f"Must select from: "
                                     f"{self.component_store.component_map.keys()}")
                        sys.exit()
                    component_selected = True
                    continue

            elif self.namespace == NameSpace.NODE:
                subcommand_indices[cur_cmd_name].append(index)

            elif self.namespace == NameSpace.STATUS:
                pass

            # print(f"subcommand_indices={subcommand_indices}, index={index}, arg={arg}")

        if self.namespace == NameSpace.START:
            if self.selected_component:
                self.new_start_options = self.extend_start_cli(self.selected_component)
        if self.namespace == NameSpace.INSTALL:
            if self.selected_component:
                self.new_install_options = self.extend_install_cli(self.selected_component)
        self.feed_to_argparsers(args, subcommand_indices)

    def generate_immutable_config(self):
        parsed_args = self.subcmd_parsed_args_map[self.namespace]
        if self.namespace == NameSpace.INSTALL:
            self.config = Config(
                namespace=self.namespace,
                selected_component=self.selected_component,
                repo=parsed_args.repo,
                branch=parsed_args.branch,
                background_flag=parsed_args.background,
                component_id=parsed_args.id,
            )
            if self.new_install_options:
                for varname in self.new_install_options:
                    value = getattr(self.subcmd_parsed_args_map[NameSpace.INSTALL], varname)
                    setattr(self.config, varname, value)
        elif self.namespace == NameSpace.START:
            self.config = Config(
                namespace=self.namespace,
                selected_component=self.selected_component,
                repo=parsed_args.repo,
                branch=parsed_args.branch,
                new_flag=parsed_args.new,
                gui_flag=parsed_args.gui,
                background_flag=parsed_args.background,
                inline_flag=parsed_args.inline,
                new_terminal_flag=parsed_args.new_terminal,
                component_id=parsed_args.id,
                component_args=self.component_args
            )
            if self.new_start_options:
                for varname in self.new_start_options:
                    value = getattr(self.subcmd_parsed_args_map[NameSpace.START], varname)
                    setattr(self.config, varname, value)
        elif self.namespace == NameSpace.RESET:
            self.config = Config(
                namespace=self.namespace,
                selected_component=self.selected_component,
                repo=parsed_args.repo,
                branch=parsed_args.branch,
                component_id=parsed_args.id,
                component_args=self.component_args
            )
        elif self.namespace == NameSpace.STOP:
            self.config = Config(
                namespace=self.namespace,
                selected_component=self.selected_component,
                component_id=parsed_args.id,
            )
        elif self.namespace == NameSpace.NODE:
            self.config = Config(
                namespace=self.namespace,
                node_args=self.node_args,
                # --id, --rpchost, --rpcport are managed manually see controller.node()
            )
        elif self.namespace in {NameSpace.STATUS, NameSpace.TOP_LEVEL}:
            self.config = Config(
                namespace=self.namespace
            )
        return self.config

    def update_subcommands_args_map(self, args, subcommand_indices):
        for namespace in subcommand_indices:
            for index in subcommand_indices[namespace]:
                self.parser_raw_args_map[namespace].append(args[index])

    def feed_to_argparsers(self, args, subcommand_indices):
        """feeds relevant arguments to each child (or parent) ArgumentParser"""
        self.update_subcommands_args_map(args, subcommand_indices)

        for cmd_name in self.parser_map:
            if cmd_name == NameSpace.NODE:
                self.node_args = self.parser_raw_args_map[cmd_name]
            else:
                parsed_args = self.parser_map[cmd_name].parse_args(
                    args=self.parser_raw_args_map[cmd_name]
                )
            self.subcmd_parsed_args_map[cmd_name] = parsed_args

    def add_install_argparser(self, namespaces):
        start_parser = namespaces.add_parser("help", help="specify which servers to run")
        start_parser.add_argument("--background", action="store_true", help="")
        start_parser.add_argument("--id", type=str, default="", help="human-readable identifier "
            "for component (e.g. 'worker1_esv')")
        start_parser.add_argument("--repo", type=str, default="", help="git repo as either an "
            "https://github.com url or a local git repo path e.g. G:/electrumsv (optional)")
        start_parser.add_argument("--branch", type=str, default="", help="git repo branch ("
            "optional)")

        # add <component_types> from plugins
        subparsers = start_parser.add_subparsers(help="subcommand", required=False)
        start_namespace_subcommands = []
        for component_type in self.component_store.component_map:
            component_parser = subparsers.add_parser(component_type,
                help=f"install {component_type}")
            start_namespace_subcommands.append(component_parser)
        return start_parser, start_namespace_subcommands

    def add_start_argparser(self, namespaces):
        start_parser = namespaces.add_parser("start", help="specify which servers to run")
        start_parser.add_argument("--new", action="store_true",
            help="run a new instance with unique 'id'")
        start_parser.add_argument("--gui", action="store_true",
            help="run in gui mode (electrumsv only)")
        start_parser.add_argument("--background", action="store_true", help="spawn in background")
        start_parser.add_argument("--inline", action="store_true", help="spawn in current shell")
        start_parser.add_argument("--new-terminal", action="store_true",
            help="spawn in a new terminal window")
        start_parser.add_argument("--id", type=str, default="", help="human-readable identifier "
            "for component (e.g. 'worker1_esv')")
        start_parser.add_argument("--repo", type=str, default="", help="git repo as either an "
            "https://github.com url or a local git repo path e.g. G:/electrumsv (optional)")
        start_parser.add_argument("--branch", type=str, default="", help="git repo branch ("
            "optional)")

        # add <component_types> from plugins
        subparsers = start_parser.add_subparsers(help="subcommand", required=False)
        start_namespace_subcommands = []
        for component_type in self.component_store.component_map:
            component_parser = subparsers.add_parser(component_type, help=f"start {component_type}")
            start_namespace_subcommands.append(component_parser)
        return start_parser, start_namespace_subcommands

    def add_stop_argparser(self, namespaces):
        stop_parser = namespaces.add_parser("stop", help="stop all spawned processes")
        stop_parser.add_argument("--id", type=str, default="", help="human-readable identifier "
            "for component (e.g. 'electrumsv1')")

        # add <component_types> from plugins
        subparsers = stop_parser.add_subparsers(help="subcommand", required=False)
        stop_namespace_subcommands = []
        for component_type in self.component_store.component_map:
            component_parser = subparsers.add_parser(component_type, help=f"stop {component_type}")
            stop_namespace_subcommands.append(component_parser)

        return stop_parser, stop_namespace_subcommands

    def add_reset_argparser(self, namespaces):
        """only relevant for component types with a DATADIR (e.g. node, electrumx, electrumsv)"""
        reset_parser = namespaces.add_parser("reset", help="reset state of relevant servers to "
            "genesis")
        reset_parser.add_argument("--id", type=str, default="", help="human-readable identifier "
            "for component (e.g. 'electrumsv1')")
        reset_parser.add_argument("--repo", type=str, default="", help="git repo as either an "
            "https://github.com url or a local git repo path e.g. G:/electrumsv (optional)")
        reset_parser.add_argument("--branch", type=str, default="", help="git repo branch ("
            "optional)")

        # add <component_types> from plugins
        subparsers = reset_parser.add_subparsers(help="subcommand", required=False)
        reset_namespace_subcommands = []
        for component_type in self.component_store.component_map:
            component_parser = subparsers.add_parser(component_type, help=f"reset {component_type}")
            reset_namespace_subcommands.append(component_parser)

        return reset_parser, reset_namespace_subcommands

    def add_node_argparser(self, namespaces):
        node_parser = namespaces.add_parser(
            "node",
            help="direct access to the built-in bitcoin daemon RPC commands",
            usage="use as you would use bitcoin-cli",
        )
        node_parser.add_argument("--rpchost", type=str, default="",
            help="rpchost defaults to 127.0.0.1")
        node_parser.add_argument("--rpcport", type=str, default="",
            help="rpchost defaults to 18332")
        node_parser.add_argument("--id", type=str, default="",
            help="select node instance by unique identifier (cannot mix this option with rpcport / "
                 "rpchost args)")
        # NOTE: all args are actually directed at the bitcoin RPC over http
        return node_parser

    def add_status_argparser(self, namespaces):
        status_parser = namespaces.add_parser(
            "status", help="get a status update of SDK applications"
        )
        return status_parser

    def add_global_flags(self, top_level_parser):
        top_level_parser.add_argument(
            "--version", action="store_true", dest="version", default=False,
            help="version information",
        )

    def setup_argparser(self):
        top_level_parser = argparse.ArgumentParser()
        self.add_global_flags(top_level_parser)

        namespaces = top_level_parser.add_subparsers(help="namespaces", required=False)
        install_parser, start_namespace_subcommands = self.add_install_argparser(namespaces)
        start_parser, start_namespace_subcommands = self.add_start_argparser(namespaces)
        stop_parser, stop_namespace_subcommands = self.add_stop_argparser(namespaces)
        reset_parser, reset_namespace_subcommands = self.add_reset_argparser(namespaces)
        node_parser = self.add_node_argparser(namespaces)
        status_parser = self.add_status_argparser(namespaces)

        # register top-level ArgumentParsers
        self.parser_map[NameSpace.TOP_LEVEL] = top_level_parser
        self.parser_map[NameSpace.INSTALL] = install_parser
        self.parser_map[NameSpace.START] = start_parser
        self.parser_map[NameSpace.STOP] = stop_parser
        self.parser_map[NameSpace.RESET] = reset_parser
        self.parser_map[NameSpace.NODE] = node_parser
        self.parser_map[NameSpace.STATUS] = status_parser

        # prepare raw_args
        for namespace in self.parser_map.keys():
            self.parser_raw_args_map[namespace] = []

    def extend_start_cli(self, selected_component: str):
        """gets attached to the Config object that is passed back into the plugin"""
        component_module = self.component_store.import_plugin_module(selected_component)
        try:
            start_parser = self.parser_map[NameSpace.START]
            start_parser, new_options = getattr(
                component_module, selected_component).extend_start_cli(start_parser)
            self.parser_map[NameSpace.START] = start_parser
            return new_options
        except AttributeError:
            # no 'extend_start_cli' method present for this plugin
            return

    def extend_install_cli(self, selected_component: str):
        """gets attached to the Config object that is passed back into the plugin"""
        component_module = self.component_store.import_plugin_module(selected_component)
        try:
            install_parser = self.parser_map[NameSpace.INSTALL]
            install_parser, new_options = getattr(
                component_module, selected_component).extend_install_cli(install_parser)
            self.parser_map[NameSpace.INSTALL] = install_parser
            return new_options
        except AttributeError:
            # no 'extend_install_cli' method present for this plugin
            return
