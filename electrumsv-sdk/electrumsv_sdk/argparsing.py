"""
As a workaround to lack of support for argparse to take multiple subcommands (+/- args)
simultaneously I manually parse sys.argv and find the relevant args to feed to the appropriate
ArgumentParser instance.

Fortunately the help menu displays as expected so does not deviate from the standard docuementation.
"""

import argparse
from argparse import RawTextHelpFormatter

from .app_state import AppState, TOP_LEVEL_HELP_TEXT


class InvalidInput(Exception):
    pass


def parse_first_arg(arg, cur_cmd_name, subcommand_indices):
    if arg == "start":
        cur_cmd_name = AppState.START
        AppState.NAMESPACE = AppState.START
        subcommand_indices[AppState.START] = []
    elif arg == AppState.STOP:
        cur_cmd_name = AppState.STOP
        AppState.NAMESPACE = AppState.STOP
        subcommand_indices[AppState.STOP] = []
    elif arg == AppState.RESET:
        cur_cmd_name = AppState.RESET
        AppState.NAMESPACE = AppState.RESET
        subcommand_indices[AppState.RESET] = []
    elif arg == AppState.NODE:
        cur_cmd_name = AppState.NODE
        AppState.NAMESPACE = AppState.NODE
        subcommand_indices[AppState.NODE] = []
    elif arg == AppState.STATUS:
        cur_cmd_name = AppState.STATUS
        AppState.NAMESPACE = AppState.STATUS
        subcommand_indices[AppState.STATUS] = []
    elif arg == "--help":
        pass
    else:
        raise InvalidInput(
            "First argument must be one of: [start, stop, reset, node, " "status, --help]"
        )
    return cur_cmd_name, subcommand_indices


def manual_argparsing(args):
    """manually iterate through sys.argv and feed arguments to either:
    a) parent ArgumentParser
    b) child ArgumentParsers (aka subcommands)"""

    args.pop(0)

    subcommand_indices = {}  # cmd_name: [index_arg1, index_arg2]

    cur_cmd_name = AppState.TOP_LEVEL
    AppState.NAMESPACE = AppState.TOP_LEVEL
    subcommand_indices[AppState.TOP_LEVEL] = []
    for index, arg in enumerate(args):
        if index == 0:
            cur_cmd_name, subcommand_indices = parse_first_arg(
                arg, cur_cmd_name, subcommand_indices
            )

        if AppState.NAMESPACE == AppState.TOP_LEVEL:
            subcommand_indices[AppState.TOP_LEVEL].append(index)

        if AppState.NAMESPACE == AppState.START:
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

        if AppState.NAMESPACE == AppState.STOP:
            pass

        if AppState.NAMESPACE == AppState.RESET:
            pass

        if AppState.NAMESPACE == AppState.NODE:
            if index != 0:
                subcommand_indices[cur_cmd_name].append(index)

        if AppState.NAMESPACE == AppState.STATUS:
            pass

        # print(f"subcommand_indices={subcommand_indices}, index={index}, arg={arg}")

    feed_to_argparsers(args, subcommand_indices)


def update_subcommands_args_map(args, subcommand_indices):
    config = AppState
    for cmd_name in subcommand_indices:
        for index in subcommand_indices[cmd_name]:
            config.subcmd_raw_args_map[cmd_name].append(args[index])


def feed_to_argparsers(args, subcommand_indices):
    """feeds relevant arguments to each child (or parent) ArgumentParser"""
    config = AppState
    update_subcommands_args_map(args, subcommand_indices)

    for cmd_name in config.subcmd_map:
        if cmd_name == AppState.NODE:
            parsed_args = config.subcmd_raw_args_map[cmd_name]
        else:
            parsed_args = config.subcmd_map[cmd_name].parse_args(
                args=config.subcmd_raw_args_map[cmd_name]
            )
        config.subcmd_parsed_args_map[cmd_name] = parsed_args


def add_start_argparser(namespaces):
    start_parser = namespaces.add_parser("start", help="specify which servers to run")

    start_parser.add_argument(
        "--full-stack", action="store_true", help="",
    )
    start_parser.add_argument(
        "--node", action="store_true", help="",
    )
    start_parser.add_argument(
        "--ex-node", action="store_true", help="",
    )
    start_parser.add_argument(
        "--esv-ex-node", action="store_true", help="",
    )
    start_parser.add_argument(
        "--esv-idx-node", action="store_true", help="",
    )

    start_parser.add_argument(
        "--extapp",
        default="",
        dest="extapp_path",
        type=str,
        help="path to 3rd party applications. The 'extapp' flag can be specified multiple times. "
        "For electrumsv 'daemon apps' please see electrumsv subcommand help menu",
    )

    subparsers = start_parser.add_subparsers(help="subcommand", required=False)

    # ELECTRUMSV
    electrumsv = subparsers.add_parser(AppState.ELECTRUMSV, help="specify repo and branch")
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

    # ELECTRUMX
    electrumx = subparsers.add_parser(AppState.ELECTRUMX, help="specify repo and branch")
    electrumx.add_argument(
        "-repo",
        type=str,
        default="",
        help="electrumx git repo as either an https://github.com url or a "
        "local git repo path e.g. G:/electrumx",
    )
    electrumx.add_argument(
        "-branch", type=str, default="", help="electrumx git repo branch (optional)",
    )

    # ELECTRUMSV-INDEXER
    electrumsv_indexer = subparsers.add_parser(
        AppState.ELECTRUMSV_INDEXER, help="specify repo and branch"
    )
    electrumsv_indexer.add_argument(
        "-repo",
        type=str,
        default="",
        help="electrumsv_indexer git repo as either an https://github.com url or a "
        "local git repo path e.g. G:/electrumsv_indexer",
    )
    electrumsv_indexer.add_argument(
        "-branch", type=str, default="", help="electrumsv_indexer git repo branch (optional)",
    )

    # ELECTRUMSV-NODE
    electrumsv_node = subparsers.add_parser(AppState.ELECTRUMSV_NODE, help="specify repo and branch")
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
    start_namespace_subcommands = [electrumsv, electrumsv_node, electrumx, electrumsv_indexer]
    return start_parser, start_namespace_subcommands


def add_stop_argparser(namespaces):
    stop_parser = namespaces.add_parser("stop", help="stop all spawned processes")
    return stop_parser


def add_reset_argparser(namespaces):
    reset_parser = namespaces.add_parser("reset", help="reset state of relevant servers to genesis")
    return reset_parser


def add_node_argparser(namespaces):
    node_parser = namespaces.add_parser(
        "node",
        help="direct access to the built-in bitcoin " "daemon RPC commands",
        usage="use as you would use bitcoin-cli",
    )

    # NOTE: this is a facade - all args are actually directed at the bitcoin RPC over http
    # including the help menu
    return node_parser


def add_status_argparser(namespaces):
    status_parser = namespaces.add_parser("node", help="get a status update of SDK applications")
    return status_parser


def setup_argparser():
    """
    Structure of CLI interface:

    top_level_parser
        start
            --full-stack
            --node
            --status-server
            --ex-node
            --esv-ex-node
            --esv-idx-node
            --extapp
            electrumsv          (subcmd of 'start' namespace for config options)
            electrumx           (subcmd of 'start' namespace for config options)
            electrumsv-indexer  (subcmd of 'start' namespace for config options)
            electrumsv-node     (subcmd of 'start' namespace for config options)
        stop
        reset
        node
        status

    """
    top_level_parser = argparse.ArgumentParser(
        description=TOP_LEVEL_HELP_TEXT, formatter_class=RawTextHelpFormatter
    )

    namespaces = top_level_parser.add_subparsers(help="namespaces", required=False)
    start_parser, start_namespace_subcommands = add_start_argparser(namespaces)
    stop_parser = add_stop_argparser(namespaces)
    reset_parser = add_reset_argparser(namespaces)
    node_parser = add_node_argparser(namespaces)
    status_parser = add_status_argparser(namespaces)

    # register top-level ArgumentParsers
    AppState.subcmd_map[AppState.TOP_LEVEL] = top_level_parser
    AppState.subcmd_map[AppState.START] = start_parser
    AppState.subcmd_map[AppState.STOP] = stop_parser
    AppState.subcmd_map[AppState.RESET] = reset_parser
    AppState.subcmd_map[AppState.NODE] = node_parser
    AppState.subcmd_map[AppState.STATUS] = status_parser

    # register subcommands second so that handlers are called in desired ordering
    for cmd in start_namespace_subcommands:
        cmd_name = cmd.prog.split(sep=" ")[2]
        AppState.subcmd_map[cmd_name] = cmd

    for cmd_name in AppState.subcmd_map.keys():
        AppState.subcmd_raw_args_map[cmd_name] = []
