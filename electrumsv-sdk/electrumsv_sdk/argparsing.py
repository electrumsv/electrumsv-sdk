"""
As a workaround to lack of support for argparse to take multiple subcommands (+/- args)
simultaneously sys.argv is manually parsed to find the relevant args to feed to the appropriate
ArgumentParser instance.

Fortunately the help menu displays as expected so does not deviate from the standard docuementation.
"""

import argparse
import logging
import textwrap
from argparse import RawTextHelpFormatter

from electrumsv_sdk.components import ComponentName

logger = logging.getLogger("argparsing")


class InvalidInput(Exception):
    pass


class ArgParser:
    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.set_help_text()

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
            pass
        else:
            raise InvalidInput(
                "First argument must be one of: [start, stop, reset, node, " "status, --help]"
            )
        return cur_cmd_name, subcommand_indices

    def manual_argparsing(self, args):
        """manually iterate through sys.argv and feed arguments to either:
        a) parent ArgumentParser
        b) child ArgumentParsers (aka subcommands)"""

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

            if self.app_state.NAMESPACE == self.app_state.TOP_LEVEL:
                subcommand_indices[self.app_state.TOP_LEVEL].append(index)

            if self.app_state.NAMESPACE == self.app_state.START:
                # 'start' top-level arguments
                if arg.startswith("--"):
                    subcommand_indices[cur_cmd_name].append(index)

                # new child ArgumentParser
                if not arg.startswith("-"):
                    cur_cmd_name = arg
                    subcommand_indices[cur_cmd_name] = []

                # child ArgumentParser arguments
                if arg.startswith("-") and not arg.startswith("--"):
                    subcommand_indices[cur_cmd_name].append(index)

            if self.app_state.NAMESPACE == self.app_state.STOP:
                if arg.startswith("--"):
                    subcommand_indices[cur_cmd_name].append(index)

            if self.app_state.NAMESPACE == self.app_state.RESET:
                pass

            if self.app_state.NAMESPACE == self.app_state.NODE:
                if index != 0:
                    subcommand_indices[cur_cmd_name].append(index)

            if self.app_state.NAMESPACE == self.app_state.STATUS:
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
        electrumsv = subparsers.add_parser(ComponentName.ELECTRUMSV, help="specify repo and branch")
        electrumsv.add_argument(
            "-repo",
            type=str,
            default="",
            help="electrumsv git repo as either an https://github.com url or a "
            "local git repo path e.g. G:/electrumsv",
        )
        electrumsv.add_argument(
            "-branch", type=str, default="", help="electrumsv git repo branch (optional)",
        )
        electrumsv.add_argument(
            "-dapp",
            default="",
            dest="dapp_path",
            type=str,
            help="load and launch a daemon app plugin on the electrumsv daemon",
        )
        return subparsers, electrumsv

    def add_subparser_electrumx(self, subparsers):
        electrumx = subparsers.add_parser(ComponentName.ELECTRUMX, help="specify repo and branch")
        electrumx.add_argument(
            "-repo",
            type=str,
            default="",
            help="electrumx git repo as either an https://github.com url or a "
            "local git repo path e.g. G:/electrumx",
        )
        electrumx.add_argument(
            "-branch", type=str, default="", help="electrumx git repo branch (optional)"
        )
        return subparsers, electrumx

    def add_subparser_indexer(self, subparsers):
        electrumsv_indexer = subparsers.add_parser(
            ComponentName.INDEXER, help="specify repo and branch"
        )
        electrumsv_indexer.add_argument(
            "-repo",
            type=str,
            default="",
            help="electrumsv_indexer git repo as either an https://github.com url or a "
            "local git repo path e.g. G:/electrumsv_indexer",
        )
        electrumsv_indexer.add_argument(
            "-branch", type=str, default="", help="electrumsv_indexer git repo branch (optional)"
        )
        return subparsers, electrumsv_indexer

    def add_subparser_node(self, subparsers):
        electrumsv_node = subparsers.add_parser(ComponentName.NODE, help="specify repo and branch")
        electrumsv_node.add_argument(
            "-repo",
            type=str,
            default="",
            help="electrumsv_node git repo as either an https://github.com url or a "
            "local git repo path e.g. G:/electrumsv_node",
        )
        electrumsv_node.add_argument(
            "-branch", type=str, default="", help="electrumsv_node git repo branch (optional)",
        )
        return subparsers, electrumsv_node

    def add_start_parser_args(self, start_parser):
        start_parser.add_argument("--full-stack", action="store_true", help="")
        start_parser.add_argument("--node", action="store_true", help="")
        start_parser.add_argument("--ex-node", action="store_true", help="")
        start_parser.add_argument("--esv-ex-node", action="store_true", help="")
        start_parser.add_argument("--esv-idx-node", action="store_true", help="")
        start_parser.add_argument(
            "--extapp",
            default="",
            dest="extapp_path",
            type=str,
            help="path to 3rd party applications. Can be specified multiple times. "
            "For electrumsv 'daemon apps' please see electrumsv subcommand help menu",
        )
        return start_parser

    def add_start_argparser(self, namespaces):
        start_parser = namespaces.add_parser("start", help="specify which servers to run")
        start_parser = self.add_start_parser_args(start_parser)

        subparsers = start_parser.add_subparsers(help="subcommand", required=False)
        subparsers, electrumsv = self.add_subparser_electrumsv(subparsers)
        subparsers, electrumx = self.add_subparser_electrumx(subparsers)
        subparsers, electrumsv_indexer = self.add_subparser_indexer(subparsers)
        subparsers, electrumsv_node = self.add_subparser_node(subparsers)

        start_namespace_subcommands = [
            electrumsv,
            electrumsv_node,
            electrumx,
            electrumsv_indexer,
        ]
        return start_parser, start_namespace_subcommands

    def add_stop_argparser(self, namespaces):
        stop_parser = namespaces.add_parser("stop", help="stop all spawned processes")
        stop_parser.add_argument("--node", action="store_true", help="stop node")
        stop_parser.add_argument("--ex", action="store_true", help="stop electrumx")
        stop_parser.add_argument("--esv", action="store_true", help="stop electrumsv")
        stop_parser.add_argument("--idx", action="store_true", help="stop indexer")
        stop_parser.add_argument("--extapp", action="store_true", help="stop extension app")
        return stop_parser

    def add_reset_argparser(self, namespaces):
        reset_parser = namespaces.add_parser(
            "reset", help="reset state of relevant servers to genesis"
        )
        return reset_parser

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
            "node", help="get a status update of SDK applications"
        )
        return status_parser

    def setup_argparser(self):
        top_level_parser = argparse.ArgumentParser(
            description=self.help_text, formatter_class=RawTextHelpFormatter
        )

        namespaces = top_level_parser.add_subparsers(help="namespaces", required=False)
        start_parser, start_namespace_subcommands = self.add_start_argparser(namespaces)
        stop_parser = self.add_stop_argparser(namespaces)
        reset_parser = self.add_reset_argparser(namespaces)
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
            run electrumsv + electrumx + electrumsv-node
                > electrumsv-sdk start --full-stack or
                > electrumsv-sdk start --esv-ex-node

            run electrumsv + electrumsv-indexer + electrumsv-node
                > electrumsv-sdk start --esv-idx-node

             -------------------------------------------------------
            | esv = electrumsv daemon                               |
            | ex = electrumx server                                 |
            | node = electrumsv-node                                |
            | idx = electrumsv-indexer (with pushdata-centric API)  |
            | full-stack = defaults to 'esv-ex-node'                |
             -------------------------------------------------------

            input the needed mixture to suit your needs

            dependencies are installed on-demand at run-time

            specify a local or remote git repo and branch for each server e.g.
                > electrumsv-sdk start --full-stack electrumsv repo=G:/electrumsv branch=develop

            'repo' can take the form repo=https://github.com/electrumsv/electrumsv.git for a remote 
            repo or repo=G:/electrumsv for a local dev repo

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
