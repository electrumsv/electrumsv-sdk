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
import signal
import subprocess
import time
from argparse import RawTextHelpFormatter
import platform
from sys import argv
import sys
import textwrap
from typing import List

from electrumsv_node import electrumsv_node

from .config import Config
from .handle_dependencies import handle_dependencies
from .runners import run_electrumsv_daemon, run_electrumsv_node, run_electrumx_server


def register_subcommands(subparsers: List[argparse.ArgumentParser]):
    config = Config
    for cmd in subparsers:
        cmd_name = cmd.prog.split(sep=" ")[1]
        config.subcmd_map.update({cmd_name: cmd})

    # initialize subcommands_args_map with empty arg list
    for cmd_name in config.subcmd_map.keys():
        config.subcmd_raw_args_map[cmd_name] = []


def manual_argparsing(args):
    """manually iterate through sys.argv and feed arguments to either:
    a) parent ArgumentParser
    b) child ArgumentParsers (aka subcommands)"""
    config = Config
    args.pop(0)

    # subcommand_indices -> cmd_name: [index_arg1, index_arg2]
    subcommand_indices = {}

    cur_cmd_name = config.ELECTRUMSV_SDK
    subcommand_indices[cur_cmd_name] = []
    for index, arg in enumerate(args):
        # parent ArgumentParser
        if arg.startswith("--") and cur_cmd_name == "electrumsv_sdk":
            subcommand_indices[cur_cmd_name].append(index)

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


def setup_argparser():
    config = Config
    help_text = textwrap.dedent(
        """

        codes:
        ------
        - esv=electrumsv daemon
        - ex=electrumx server
        - node=electrumsv-node
        - idx=electrumsv-indexer (with pushdata-centric API)
        - full-stack=defaults to 'esv-ex-node' as these are the default run-time
        dependencies of electrumsv as of July 2020.

        examples:
        > electrumsv-sdk --full-stack or
        > electrumsv-sdk --esv-ex-node
        will run electrumsv + electrumx + electrumsv-node (both have equivalent effect)

        > electrumsv-sdk --esv-idx-node
        will run electrumsv + electrumsv-indexer + electrumsv-node

        dependencies are installed on-demand at run-time

        specify which local or remote (git repo) and branch for each component with the 
        subcommands below. ('repo' can take the form: 
        - repo=https://github.com/electrumsv/electrumsv.git or 
        - repo=G:/electrumsv for a local dev repo)

        > electrumsv-sdk --full-stack electrumsv repo=G:/electrumsv branch=develop

        all arguments are optional
        """
    )
    parser = argparse.ArgumentParser(
        description=help_text, formatter_class=RawTextHelpFormatter
    )
    parser.add_argument(
        "--full-stack", action="store_true", help="",
    )
    parser.add_argument(
        "--node", action="store_true", help="",
    )
    parser.add_argument(
        "--ex-node", action="store_true", help="",
    )
    parser.add_argument(
        "--esv-ex-node", action="store_true", help="",
    )
    parser.add_argument(
        "--esv-idx-node", action="store_true", help="",
    )

    parser.add_argument(
        "--extapp",
        default="",
        dest="extapp_path",
        type=str,
        help="path to 3rd party applications. The 'extapp' flag can be specified multiple times. "
             "For electrumsv 'daemon apps' please see electrumsv subcommand help menu",
    )

    subparsers = parser.add_subparsers(help="subcommand", required=False)

    # ELECTRUMSV
    electrumsv = subparsers.add_parser(
        config.ELECTRUMSV, help="specify repo and branch"
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
    electrumx = subparsers.add_parser(config.ELECTRUMX, help="specify repo and branch")
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
        config.ELECTRUMSV_INDEXER, help="specify repo and branch"
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
        config.ELECTRUMSV_NODE, help="specify repo and branch"
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
    subparsers_list = [electrumsv, electrumx, electrumsv_node, electrumsv_indexer]
    config.subcmd_map[config.ELECTRUMSV_SDK] = parser  # register parent ArgumentParser
    register_subcommands(subparsers_list)

def startup():
    print()
    print()
    print("running stack...")
    procs = []
    if 'electrumsv_node' in Config.required_dependencies_set:
        run_electrumsv_node()

    if 'electrumx' in Config.required_dependencies_set:
        electrumx_process = run_electrumx_server()
        procs.append(electrumx_process)

    if 'electrumsv' in Config.required_dependencies_set:
        esv_process = run_electrumsv_daemon()
        procs.append(esv_process)
    return procs

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

    Note: all configuration is saved to / loaded from config.json and each function accesses it
    by dependency-injection.
    """
    procs = []
    try:
        print("ElectrumSV Software Development Kit")
        print(
            f"-Python version {sys.version_info.major}.{sys.version_info.minor}."
            f"{sys.version_info.micro}-{platform.architecture()[0]}"
        )
        print()

        setup_argparser()
        manual_argparsing(argv)  # updates global 'Config.subcmd_parsed_args_map'
        handle_dependencies()
        procs = startup()

        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        electrumsv_node.stop()

        # Todo - this doesn't work
        if len(procs) != 0:
            for proc in procs:
                subprocess.run(f"taskkill.exe /PID {proc.pid} /T /F")
        print("stack terminated")
