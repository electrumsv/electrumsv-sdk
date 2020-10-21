"""
As a workaround to lack of support for argparse to take multiple subcommands (+/- args)
simultaneously sys.argv is manually parsed to find the relevant args to feed to the appropriate
ArgumentParser instance.

Fortunately the help menu displays as expected so does not deviate from the standard docuementation.
"""

import argparse
import logging
import sys
import textwrap
from argparse import RawTextHelpFormatter

from .components import ComponentStore

logger = logging.getLogger("argparsing")


class NameSpace:
    TOP_LEVEL = "top_level"
    START = "start"
    STOP = "stop"
    RESET = "reset"
    NODE = "node"
    STATUS = 'status'


class ArgParser:
    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.set_help_text()
        self.component_store = ComponentStore(self.app_state)

    def parse_first_arg(self, arg, cur_cmd_name, subcommand_indices):
        if arg in {NameSpace.START, NameSpace.STOP, NameSpace.RESET, NameSpace.NODE,
                   NameSpace.STATUS}:
            cur_cmd_name = arg
            self.app_state.NAMESPACE = arg
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

    def manual_argparsing(self, args):
        """manually iterate through sys.argv and feed arguments to either:
        a) parent ArgumentParser
        b) child ArgumentParsers (aka subcommands)"""
        component_selected = False
        args.pop(0)

        subcommand_indices = {}  # cmd_name: [index_arg1, index_arg2]

        cur_cmd_name = NameSpace.TOP_LEVEL
        self.app_state.NAMESPACE = NameSpace.TOP_LEVEL
        subcommand_indices[NameSpace.TOP_LEVEL] = []
        for index, arg in enumerate(args):
            if index == 0:
                cur_cmd_name, subcommand_indices = self.parse_first_arg(
                    arg, cur_cmd_name, subcommand_indices
                )
                continue

            elif self.app_state.NAMESPACE == NameSpace.TOP_LEVEL:
                subcommand_indices[NameSpace].append(index)

            elif self.app_state.NAMESPACE == NameSpace.START:
                # <start options>
                if arg.startswith("--") and not component_selected:
                    subcommand_indices[cur_cmd_name].append(index)
                    continue

                # <component name>
                elif not arg.startswith("-") and not component_selected:
                    cur_cmd_name = arg
                    subcommand_indices[cur_cmd_name] = []
                    if arg in self.app_state.component_map.keys():
                        self.app_state.selected_component = arg
                    else:
                        logger.error(f"Must select from: {self.app_state.component_map.keys()}")
                        sys.exit()
                    component_selected = True
                    continue

                # <arguments to pass to component> (e.g. to standard electrumsv cli interface)
                elif component_selected:
                    self.app_state.component_args.append(arg)
                    continue

            elif self.app_state.NAMESPACE == NameSpace.STOP:
                # <stop options>
                if arg.startswith("--") and not component_selected:
                    subcommand_indices[cur_cmd_name].append(index)
                    continue

                # <component name>
                if not arg.startswith("-") and not component_selected:
                    cur_cmd_name = arg
                    subcommand_indices[cur_cmd_name] = []
                    if arg in self.app_state.component_map.keys():
                        self.app_state.selected_component = arg
                    else:
                        logger.error(f"Must select from: {self.app_state.component_map.keys()}")
                        sys.exit()
                    component_selected = True
                    continue

            elif self.app_state.NAMESPACE == NameSpace.RESET:
                # <reset options>
                if arg.startswith("--") and not component_selected:
                    subcommand_indices[cur_cmd_name].append(index)
                    continue

                # <component name>
                if not arg.startswith("-") and not component_selected:
                    cur_cmd_name = arg
                    subcommand_indices[cur_cmd_name] = []
                    if arg in self.app_state.component_map.keys():
                        self.app_state.selected_component = arg
                    else:
                        logger.error(f"Must select from: {self.app_state.component_map.keys()}")
                        sys.exit()
                    component_selected = True
                    continue

            elif self.app_state.NAMESPACE == NameSpace.NODE:
                subcommand_indices[cur_cmd_name].append(index)

            elif self.app_state.NAMESPACE == NameSpace.STATUS:
                pass

            # print(f"subcommand_indices={subcommand_indices}, index={index}, arg={arg}")
        self.feed_to_argparsers(args, subcommand_indices)

    def update_subcommands_args_map(self, args, subcommand_indices):
        for namespace in subcommand_indices:
            for index in subcommand_indices[namespace]:
                self.app_state.parser_raw_args_map[namespace].append(args[index])

    def feed_to_argparsers(self, args, subcommand_indices):
        """feeds relevant arguments to each child (or parent) ArgumentParser"""
        self.update_subcommands_args_map(args, subcommand_indices)

        for cmd_name in self.app_state.parser_map:
            if cmd_name == NameSpace.NODE:
                parsed_args = self.app_state.parser_raw_args_map[cmd_name]
            else:
                parsed_args = self.app_state.parser_map[cmd_name].parse_args(
                    args=self.app_state.parser_raw_args_map[cmd_name]
                )
            self.app_state.parser_parsed_args_map[cmd_name] = parsed_args

    def add_start_argparser(self, namespaces):
        start_parser = namespaces.add_parser("start", help="specify which servers to run")
        start_parser.add_argument("--new", action="store_true", help="")
        start_parser.add_argument("--gui", action="store_true", help="")
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
        for component_type in self.app_state.component_map:
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
        for component_type in self.app_state.component_map:
            component_parser = subparsers.add_parser(component_type, help=f"stop {component_type}")
            stop_namespace_subcommands.append(component_parser)

        return stop_parser, stop_namespace_subcommands

    def add_reset_argparser(self, namespaces):
        """only relevant for component types with a datadir (e.g. node, electrumx, electrumsv)"""
        reset_parser = namespaces.add_parser("reset", help="reset state of relevant servers to "
            "genesis")
        reset_parser.add_argument("--id", type=str, default="", help="human-readable identifier "
            "for component (e.g. 'electrumsv1')")
        reset_parser.add_argument("--repo", type=str, default="", help="git repo as either an "
            "https://github.com url or a local git repo path e.g. G:/electrumsv (optional)")

        # add <component_types> from plugins
        subparsers = reset_parser.add_subparsers(help="subcommand", required=False)
        reset_namespace_subcommands = []
        for component_type in self.app_state.component_map:
            component_parser = subparsers.add_parser(component_type, help=f"reset {component_type}")
            reset_namespace_subcommands.append(component_parser)

        return reset_parser, reset_namespace_subcommands

    def add_node_argparser(self, namespaces):
        node_parser = namespaces.add_parser(
            "node",
            help="direct access to the built-in bitcoin " "daemon RPC commands",
            usage="use as you would use bitcoin-cli",
        )
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
        top_level_parser = argparse.ArgumentParser(
            description=self.help_text, formatter_class=RawTextHelpFormatter
        )
        self.add_global_flags(top_level_parser)

        namespaces = top_level_parser.add_subparsers(help="namespaces", required=False)
        start_parser, start_namespace_subcommands = self.add_start_argparser(namespaces)
        stop_parser, stop_namespace_subcommands = self.add_stop_argparser(namespaces)
        reset_parser, reset_namespace_subcommands = self.add_reset_argparser(namespaces)
        node_parser = self.add_node_argparser(namespaces)
        status_parser = self.add_status_argparser(namespaces)

        # register top-level ArgumentParsers
        self.app_state.parser_map[NameSpace.TOP_LEVEL] = top_level_parser
        self.app_state.parser_map[NameSpace.START] = start_parser
        self.app_state.parser_map[NameSpace.STOP] = stop_parser
        self.app_state.parser_map[NameSpace.RESET] = reset_parser
        self.app_state.parser_map[NameSpace.NODE] = node_parser
        self.app_state.parser_map[NameSpace.STATUS] = status_parser

        # prepare raw_args
        for namespace in self.app_state.parser_map.keys():
            self.app_state.parser_raw_args_map[namespace] = []

    def set_help_text(self):
        self.help_text = textwrap.dedent(
            """
            top-level
            =========
            electrumsv-sdk has four top-level namespaces (and works similarly to systemctl):
            - "start"
            - "stop"
            - "reset"
            - "node"
            - "status"

            The "start" command is the most feature-rich and launches servers as background
            processes (see next):

            start
            =====
            examples:
            run node + electrumx + electrumsv
                > electrumsv-sdk start node
                > electrumsv-sdk start electrumx
                > electrumsv-sdk start electrumsv

            run new instances:
                > electrumsv-sdk start --new node

            run new instances with user-defined --id
                > electrumsv-sdk start --new --id=myspecialnode node

            dependencies are installed on-demand at run-time

            specify --repo as a local path or remote git url for each component type.
                > electrumsv-sdk start --repo=G:\electrumsv electrumsv
            specify --branch as either "master" or "features/my-feature-branch"
                > electrumsv-sdk start --branch=master electrumsv

            all arguments are optional

            stop
            ====
            stops all running servers/spawned processes

            reset
            =====
            resets server state. e.g.
            - bitcoin node state is reset back to genesis
            - electrumx state is reset back to genesis
            - electrumsv RegTest wallet history is erased to match blockchain state e.g.
                > electrumsv-sdk reset

            node
            ====
            direct access to the standard bitcoin JSON-RPC interface e.g.
                > electrumsv-sdk node help
                > electrumsv-sdk node generate 10

            status
            ======
            returns a status report of applications previously started by the SDK

            """
        )

    def no_start_component_selected(self, namespace, component_selected):
        if namespace == self.app_state.START and not component_selected:
            return False
        return True

    def no_stop_component_selected(self, namespace, component_selected):
        if namespace == self.app_state.START and not component_selected:
            return False
        return True
