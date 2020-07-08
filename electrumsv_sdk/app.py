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
import textwrap
from argparse import RawTextHelpFormatter
from sys import argv
import sys
import platform
from typing import List, Dict

# subcommands_map -> cmd_name: ArgumentParser (parent or children)
subcommands_map: Dict[str, argparse.ArgumentParser] = {}

# subcommands_args_map -> cmd_name: list of arguments
subcommands_args_map: Dict[str, List[str]] = {}

# parser_args_map -> cmd_name: list of parsed arguments
parsed_args_map = {}


def register_subcommands(subparsers: List[argparse.ArgumentParser]):
    for cmd in subparsers:
        cmd_name = cmd.prog.split(sep=" ")[1]
        subcommands_map.update({cmd_name: cmd})

    # initialize subcommands_args_map with empty arg list
    for cmd_name in subcommands_map.keys():
        subcommands_args_map[cmd_name] = []


def manual_argparsing(args):
    """manually iterate through sys.argv and feed arguments to either:
    a) parent ArgumentParser
    b) child ArgumentParsers (aka subcommands)"""
    args.pop(0)

    # subcommand_indices -> cmd_name: [index_arg1, index_arg2]
    subcommand_indices = {}

    cur_cmd_name = "electrumsv_sdk"
    for index, arg in enumerate(args):
        # parent ArgumentParser
        if (
            arg.startswith("-") or arg.startswith("-")
        ) and cur_cmd_name == "electrumsv_sdk":
            subcommand_indices[cur_cmd_name] = [index]

        # child ArgumentParser (aka a subcommand)
        if not arg.startswith("-"):  # new subcommand
            cur_cmd_name = arg
            subcommand_indices[cur_cmd_name] = []

        # child ArgumentParser arguments
        if arg.startswith("-") and cur_cmd_name != "electrumsv_sdk":
            subcommand_indices[cur_cmd_name].append(index)

    # print(f"subcommand_indices={subcommand_indices}")
    feed_to_argparsers(args, subcommand_indices)


def update_subcommands_args_map(args, subcommand_indices):
    for cmd_name in subcommand_indices:
        for index in subcommand_indices[cmd_name]:
            subcommands_args_map[cmd_name].append(args[index])


def feed_to_argparsers(args, subcommand_indices):
    """feeds relevant arguments to each child (or parent) ArgumentParser"""
    update_subcommands_args_map(args, subcommand_indices)

    for cmd_name in subcommands_map:
        parsed_args = subcommands_map[cmd_name].parse_args(
            args=subcommands_args_map[cmd_name]
        )
        parsed_args_map[cmd_name] = parsed_args
        print(f"{cmd_name}: {parsed_args}")



def main():
    """
    Command-line interface for the ElectrumSV Software Development Kit

    The argparser module does not seem to naturally support the use of
    multiple subcommands simultaneously (which we need to support). This is handled
    manually by parsing sys.argv and feeding the correct options to the correct
    ArgumentParser instance (for the given subcommand). So in the end we get both
    a) the help menu interface via built-in argparser module
    b) the ability to string multiple subcommands + optional args together into a single cli
    command.
    """
    print("ElectrumSV Software Development Kit")
    print(
        f"-Python version {sys.version_info.major}.{sys.version_info.minor}."
        f"{sys.version_info.micro}-{platform.architecture()[0]}"
    )
    print()

    help_text = textwrap.dedent("""

        codes:
        ------
        - esv=electrumsv daemon
        - ex=electrumx server
        - node=electrumsv-node
        - idx=electrumsv-indexer (with pushdata-centric API)
        - full-stack=defaults to 'esv-ex-node' as these are the default run-time
        dependencies of electrumsv as of July 2020.

        examples:
        > electrumsv-sdk --run full-stack or
        > electrumsv-sdk --run esv-ex-node
        will run electrumsv + electrumx + electrumsv-node (both have equivalent effect)
        
        > electrumsv-sdk --run esv-idx-node
        will run electrumsv + electrumsv-indexer + electrumsv-node
        
        dependencies are installed on-demand at run-time
        
        specify which local or remote (git repo) and branch for each component with the 
        subcommands below. ('repo' can take the form: 
        - repo=https://github.com/electrumsv/electrumsv.git or 
        - repo=G:/electrumsv for a local dev repo)
        
        > electrumsv-sdk --run full-stack electrumsv repo=G:/electrumsv branch=develop
        
        all arguments are optional
        """)
    parser = argparse.ArgumentParser(description=help_text, formatter_class=RawTextHelpFormatter)
    parser.add_argument(
        "--run",
        default="",
        type=str,
        choices=['full-stack', 'node', 'ex-node', 'esv-ex-node', 'esv-idx-node'],
        help=""
    )
    parser.add_argument(
        "--dapp",
        default="",
        dest="dapp_path",
        type=str,
        help=""
    )

    subparsers = parser.add_subparsers(help="subcommand", required=False)

    # ELECTRUMSV
    electrumsv = subparsers.add_parser("electrumsv", help="specify repo and branch")
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

    # ELECTRUMX
    electrumx = subparsers.add_parser("electrumx", help="specify repo and branch")
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
        "electrumsv_indexer", help="specify repo and branch"
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
        "electrumsv_node", help="specify repo and branch"
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
    subparsers_list = [electrumsv, electrumx, electrumsv_indexer, electrumsv_node]
    subcommands_map["electrumsv_sdk"] = parser  # register parent ArgumentParser
    register_subcommands(subparsers_list)
    manual_argparsing(argv)  # updates global parsed_args_map
    # print(parsed_args_map)
