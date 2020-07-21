"""
In a nutshell I needed to workaround the lack of support for argparse to take multiple
subcommands (+/- args) simultaneously.

The help menu displays how I would like so I have stayed with usual conventions / standard
docs.

But in order to actually feed the arguments to the 2nd or 3rd subcommand, I manually parse
sys.argv and find the relevant args to feed to the appropriate ArgumentParser instance
(either the top-level parent or one of the child ArgumentParsers)
"""

import argparse
from argparse import RawTextHelpFormatter

from .config import Config, TOP_LEVEL_HELP_TEXT


class InvalidInput(Exception):
    pass


def manual_argparsing(args):
    """manually iterate through sys.argv and feed arguments to either:
    a) parent ArgumentParser
    b) child ArgumentParsers (aka subcommands)"""
    args.pop(0)

    # subcommand_indices -> cmd_name: [index_arg1, index_arg2]
    subcommand_indices = {}

    cur_cmd_name = Config.TOP_LEVEL
    Config.NAMESPACE = Config.TOP_LEVEL
    subcommand_indices[Config.TOP_LEVEL] = []
    for index, arg in enumerate(args):
        if index == 0:
            if arg == 'start':
                cur_cmd_name = Config.START
                Config.NAMESPACE = Config.START
                subcommand_indices[Config.START] = []
            elif arg == Config.STOP:
                cur_cmd_name = Config.STOP
                Config.NAMESPACE = Config.STOP
                subcommand_indices[Config.STOP] = []
            elif arg == Config.RESET:
                cur_cmd_name = Config.RESET
                Config.NAMESPACE = Config.RESET
                subcommand_indices[Config.RESET] = []
            elif arg == '--help':
                pass
            else:
                raise InvalidInput("First argument must be one of: [start, stop, reset, --help]")

        # TOP_LEVEL NAMESPACE (first argument was *not* one of 'start', 'stop' or 'reset'.
        # Most likely they did:
        #   > electrumsv-sdk --help
        if Config.NAMESPACE == Config.TOP_LEVEL:
            subcommand_indices[Config.TOP_LEVEL].append(index)

        # START NAMESPACE
        if Config.NAMESPACE == Config.START:
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

        # STOP NAMESPACE
        if Config.NAMESPACE == Config.STOP:
            pass

        # RESET NAMESPACE
        if Config.NAMESPACE == Config.RESET:
            pass

        # print(f"index={index}, arg={arg}, subcommand_indices={subcommand_indices}")

    feed_to_argparsers(args, subcommand_indices)


def update_subcommands_args_map(args, subcommand_indices):
    config = Config
    for cmd_name in subcommand_indices:
        for index in subcommand_indices[cmd_name]:
            config.subcmd_raw_args_map[cmd_name].append(args[index])


def feed_to_argparsers(args, subcommand_indices):
    """feeds relevant arguments to each child (or parent) ArgumentParser"""
    config = Config
    update_subcommands_args_map(args, subcommand_indices)

    for cmd_name in config.subcmd_map:
        parsed_args = config.subcmd_map[cmd_name].parse_args(
            args=config.subcmd_raw_args_map[cmd_name]
        )
        config.subcmd_parsed_args_map[cmd_name] = parsed_args
        # print(f"{cmd_name}: {parsed_args}")


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
    electrumsv = subparsers.add_parser(
        Config.ELECTRUMSV, help="specify repo and branch"
    )
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
    electrumx = subparsers.add_parser(Config.ELECTRUMX, help="specify repo and branch")
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
        Config.ELECTRUMSV_INDEXER, help="specify repo and branch"
    )
    electrumsv_indexer.add_argument(
        "-repo",
        type=str,
        default="",
        help="electrumsv_indexer git repo as either an https://github.com url or a "
        "local git repo path e.g. G:/electrumsv_indexer",
    )
    electrumsv_indexer.add_argument(
        "-branch",
        type=str,
        default="",
        help="electrumsv_indexer git repo branch (optional)",
    )

    # ELECTRUMSV-NODE
    electrumsv_node = subparsers.add_parser(
        Config.ELECTRUMSV_NODE, help="specify repo and branch"
    )
    electrumsv_node.add_argument(
        "-repo",
        type=str,
        default="",
        help="electrumsv_node git repo as either an https://github.com url or a "
        "local git repo path e.g. G:/electrumsv_node",
    )
    electrumsv_node.add_argument(
        "-branch",
        type=str,
        default="",
        help="electrumsv_node git repo branch (optional)",
    )
    start_namespace_subcommands = [electrumsv, electrumsv_node, electrumx, electrumsv_indexer]
    return start_parser, start_namespace_subcommands

def add_stop_argparser(namespaces):
    stop_parser = namespaces.add_parser("stop", help="stop all servers/spawned processes")
    return stop_parser


def add_reset_argparser(namespaces):
    reset_parser = namespaces.add_parser("reset", help="reset state of relevant servers to genesis")
    return reset_parser


def setup_argparser():
    """
    Structure of CLI interface:

    top_level_parser
        start
            --full-stack
            --node
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

    """
    top_level_parser = argparse.ArgumentParser(
        description=TOP_LEVEL_HELP_TEXT, formatter_class=RawTextHelpFormatter
    )

    namespaces = top_level_parser.add_subparsers(help="namespaces", required=False)
    start_parser, start_namespace_subcommands = add_start_argparser(namespaces)
    stop_parser = add_stop_argparser(namespaces)
    reset_parser = add_reset_argparser(namespaces)

    # register top-level ArgumentParsers
    Config.subcmd_map[Config.TOP_LEVEL] = top_level_parser
    Config.subcmd_map[Config.START] = start_parser
    Config.subcmd_map[Config.STOP] = stop_parser
    Config.subcmd_map[Config.RESET] = reset_parser

    for cmd in start_namespace_subcommands:
        cmd_name = cmd.prog.split(sep=" ")[2]
        Config.subcmd_map[cmd_name] = cmd

    # initialize subcommands_args_map with empty arg list
    for cmd_name in Config.subcmd_map.keys():
        Config.subcmd_raw_args_map[cmd_name] = []
