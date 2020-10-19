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

from .components import ComponentName, ComponentStore

logger = logging.getLogger("argparsing")


class ArgParser:
    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.set_help_text()
        self.component_store = ComponentStore(self.app_state)

    def parse_first_arg(self, arg, cur_cmd_name, subcommand_indices):
        if arg == "start":
            cur_cmd_name = self.app_state.START
            self.app_state.NAMESPACE = self.app_state.START
            subcommand_indices[self.app_state.START] = []
        elif arg == self.app_state.STOP:
            cur_cmd_name = self.app_state.STOP
            self.app_state.NAMESPACE = self.app_state.STOP
            subcommand_indices[self.app_state.STOP] = []
        elif arg == self.app_state.RESET:
            cur_cmd_name = self.app_state.RESET
            self.app_state.NAMESPACE = self.app_state.RESET
            subcommand_indices[self.app_state.RESET] = []
        elif arg == self.app_state.NODE:
            cur_cmd_name = self.app_state.NODE
            self.app_state.NAMESPACE = self.app_state.NODE
            subcommand_indices[self.app_state.NODE] = []
        elif arg == self.app_state.STATUS:
            cur_cmd_name = self.app_state.STATUS
            self.app_state.NAMESPACE = self.app_state.STATUS
            subcommand_indices[self.app_state.STATUS] = []
        elif arg == "--help":
            subcommand_indices[self.app_state.TOP_LEVEL].append(0)
        elif arg == "--version":
            subcommand_indices[self.app_state.TOP_LEVEL].append(0)
        else:
            logger.error("First argument must be one of: "
                "[start, stop, reset, node, status, --help, --version]")
            sys.exit()
        return cur_cmd_name, subcommand_indices

    def manual_argparsing(self, args):
        """manually iterate through sys.argv and feed arguments to either:
        a) parent ArgumentParser
        b) child ArgumentParsers (aka subcommands)"""
        component_selected = False
        args.pop(0)

        subcommand_indices = {}  # cmd_name: [index_arg1, index_arg2]

        cur_cmd_name = self.app_state.TOP_LEVEL
        self.app_state.NAMESPACE = self.app_state.TOP_LEVEL
        subcommand_indices[self.app_state.TOP_LEVEL] = []
        for index, arg in enumerate(args):
            if index == 0:
                cur_cmd_name, subcommand_indices = self.parse_first_arg(
                    arg, cur_cmd_name, subcommand_indices
                )
                continue

            elif self.app_state.NAMESPACE == self.app_state.TOP_LEVEL:
                subcommand_indices[self.app_state.TOP_LEVEL].append(index)

            elif self.app_state.NAMESPACE == self.app_state.START:
                # <start options>
                if arg.startswith("--") and not component_selected:
                    subcommand_indices[cur_cmd_name].append(index)
                    continue

                # <component name>
                elif not arg.startswith("-") and not component_selected:
                    cur_cmd_name = arg
                    subcommand_indices[cur_cmd_name] = []
                    if arg in ComponentName.__dict__.values():
                        self.app_state.selected_start_component = arg
                    else:
                        logger.error(f"Must select from: {self.component_store.component_list}")
                        sys.exit()
                    component_selected = True
                    continue

                # <arguments to pass to component> (e.g. to standard electrumsv cli interface)
                elif component_selected:
                    self.app_state.component_args.append(arg)
                    continue

            elif self.app_state.NAMESPACE == self.app_state.STOP:
                # <stop options>
                if arg.startswith("--") and not component_selected:
                    subcommand_indices[cur_cmd_name].append(index)
                    continue

                # <component name>
                if not arg.startswith("-") and not component_selected:
                    cur_cmd_name = arg
                    subcommand_indices[cur_cmd_name] = []
                    if arg in ComponentName.__dict__.values():
                        self.app_state.selected_stop_component = arg
                    else:
                        logger.error("Must select from: node, electrumx, electrumsv, indexer, "
                              "status_monitor]")
                        sys.exit()
                    component_selected = True
                    continue

            elif self.app_state.NAMESPACE == self.app_state.RESET:
                # <reset options>
                if arg.startswith("--") and not component_selected:
                    subcommand_indices[cur_cmd_name].append(index)
                    continue

                # <component name>
                if not arg.startswith("-") and not component_selected:
                    cur_cmd_name = arg
                    subcommand_indices[cur_cmd_name] = []
                    if arg in ComponentName.__dict__.values():
                        self.app_state.selected_reset_component = arg
                    else:
                        logger.error(f"Must select from: {self.component_store.component_list}")
                        sys.exit()
                    component_selected = True
                    continue

            elif self.app_state.NAMESPACE == self.app_state.NODE:
                subcommand_indices[cur_cmd_name].append(index)

            elif self.app_state.NAMESPACE == self.app_state.STATUS:
                pass

            # print(f"subcommand_indices={subcommand_indices}, index={index}, arg={arg}")
        self.feed_to_argparsers(args, subcommand_indices)

    def update_subcommands_args_map(self, args, subcommand_indices):
        for cmd_name in subcommand_indices:
            for index in subcommand_indices[cmd_name]:
                self.app_state.subcmd_raw_args_map[cmd_name].append(args[index])

    def feed_to_argparsers(self, args, subcommand_indices):
        """feeds relevant arguments to each child (or parent) ArgumentParser"""
        self.update_subcommands_args_map(args, subcommand_indices)

        for cmd_name in self.app_state.subcmd_map:
            if cmd_name == self.app_state.NODE:
                parsed_args = self.app_state.subcmd_raw_args_map[cmd_name]
            else:
                parsed_args = self.app_state.subcmd_map[cmd_name].parse_args(
                    args=self.app_state.subcmd_raw_args_map[cmd_name]
                )
            self.app_state.subcmd_parsed_args_map[cmd_name] = parsed_args

    def add_subparser_electrumsv(self, subparsers):
        electrumsv = subparsers.add_parser(ComponentName.ELECTRUMSV, help="start electrumsv")
        return subparsers, electrumsv

    def add_subparser_electrumsv_node(self, subparsers):
        node = subparsers.add_parser(ComponentName.NODE, help="start node")
        return subparsers, node

    def add_subparser_electrumx(self, subparsers):
        electrumx = subparsers.add_parser(ComponentName.ELECTRUMX, help="start electrumx")
        return subparsers, electrumx

    def add_subparser_indexer(self, subparsers):
        electrumsv = subparsers.add_parser(ComponentName.INDEXER, help="start indexer")
        return subparsers, electrumsv

    def add_subparser_status_monitor(self, subparsers):
        status_monitor = subparsers.add_parser(ComponentName.STATUS_MONITOR,
            help="start status monitor")
        return subparsers, status_monitor

    def add_subparser_woc(self, subparsers):
        woc = subparsers.add_parser(ComponentName.WHATSONCHAIN, help="start whatsonchain explorer")
        return subparsers, woc

    def add_start_parser_args(self, start_parser):
        start_parser.add_argument("--new", action="store_true", help="")
        start_parser.add_argument("--gui", action="store_true", help="")
        start_parser.add_argument("--background", action="store_true", help="")
        start_parser.add_argument(
            "--id",
            type=str,
            default="",
            help="human-readable identifier for component (e.g. 'worker1_esv')",
        )
        start_parser.add_argument(
            "--repo",
            type=str,
            default="",
            help="git repo as either an https://github.com url or a local git repo path "
                 "e.g. G:/electrumsv (optional)",
        )
        start_parser.add_argument(
            "--branch",
            type=str,
            default="",
            help="git repo branch (optional)"
        )
        return start_parser

    def add_start_argparser(self, namespaces):
        start_parser = namespaces.add_parser("start", help="specify which servers to run")
        start_parser = self.add_start_parser_args(start_parser)

        subparsers = start_parser.add_subparsers(help="subcommand", required=False)
        subparsers, electrumsv = self.add_subparser_electrumsv(subparsers)
        subparsers, electrumx = self.add_subparser_electrumx(subparsers)
        subparsers, status = self.add_subparser_status_monitor(subparsers)
        subparsers, electrumsv_node = self.add_subparser_electrumsv_node(subparsers)
        subparsers, electrumsv_indexer = self.add_subparser_indexer(subparsers)
        subparsers, woc = self.add_subparser_woc(subparsers)

        start_namespace_subcommands = [
            electrumsv,
            electrumx,
            status,
            electrumsv_node,
            electrumsv_indexer,
            woc,
        ]
        return start_parser, start_namespace_subcommands

    def add_stop_argparser(self, namespaces):
        stop_parser = namespaces.add_parser("stop", help="stop all spawned processes")
        stop_parser.add_argument(
            "--id",
            type=str,
            default="",
            help="human-readable identifier for component (e.g. 'electrumsv1')",
        )

        # Stop based on ComponentName
        subparsers = stop_parser.add_subparsers(help="subcommand", required=False)
        electrumsv_node = subparsers.add_parser(ComponentName.NODE, help="stop node")
        electrumx = subparsers.add_parser(ComponentName.ELECTRUMX, help="stop electrumx")
        electrumsv = subparsers.add_parser(ComponentName.ELECTRUMSV, help="stop electrumsv")
        electrumsv_indexer = subparsers.add_parser(ComponentName.INDEXER, help="stop indexer")
        status = subparsers.add_parser(ComponentName.STATUS_MONITOR, help="stop status monitor")

        stop_namespace_subcommands = [
            electrumsv,
            electrumsv_node,
            electrumx,
            electrumsv_indexer,
            status,
        ]
        return stop_parser, stop_namespace_subcommands

    def add_reset_argparser(self, namespaces):
        reset_parser = namespaces.add_parser(
            "reset", help="reset state of relevant servers to genesis"
        )
        reset_parser.add_argument(
            "--id",
            type=str,
            default="",
            help="human-readable identifier for component (e.g. 'electrumsv1')",
        )
        reset_parser.add_argument(
            "--repo",
            type=str,
            default="",
            help="git repo as either an https://github.com url or a local git repo path "
                 "e.g. G:/electrumsv (optional)",
        )
        reset_parser.add_argument(
            "--branch",
            type=str,
            default="",
            help="git repo branch (optional)"
        )

        # Stop based on ComponentName
        subparsers = reset_parser.add_subparsers(help="subcommand", required=False)
        electrumsv_node = subparsers.add_parser(ComponentName.NODE, help="reset node")
        electrumx = subparsers.add_parser(ComponentName.ELECTRUMX, help="reset electrumx")
        electrumsv = subparsers.add_parser(ComponentName.ELECTRUMSV, help="reset electrumsv")
        electrumsv_indexer = subparsers.add_parser(ComponentName.INDEXER, help="reset indexer")
        status = subparsers.add_parser(ComponentName.STATUS_MONITOR, help="reset status monitor")

        reset_namespace_subcommands = [
            electrumsv,
            electrumsv_node,
            electrumx,
            electrumsv_indexer,
            status,
        ]
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
        self.app_state.subcmd_map[self.app_state.TOP_LEVEL] = top_level_parser
        self.app_state.subcmd_map[self.app_state.START] = start_parser
        self.app_state.subcmd_map[self.app_state.STOP] = stop_parser
        self.app_state.subcmd_map[self.app_state.RESET] = reset_parser
        self.app_state.subcmd_map[self.app_state.NODE] = node_parser
        self.app_state.subcmd_map[self.app_state.STATUS] = status_parser

        # register subcommands second so that handlers are called in desired ordering
        for cmd in start_namespace_subcommands:
            cmd_name = cmd.prog.split(sep=" ")[2]
            self.app_state.subcmd_map[cmd_name] = cmd

        for cmd in stop_namespace_subcommands:
            cmd_name = cmd.prog.split(sep=" ")[2]
            self.app_state.subcmd_map[cmd_name] = cmd

        for cmd in reset_namespace_subcommands:
            cmd_name = cmd.prog.split(sep=" ")[2]
            self.app_state.subcmd_map[cmd_name] = cmd

        for cmd_name in self.app_state.subcmd_map.keys():
            self.app_state.subcmd_raw_args_map[cmd_name] = []

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
