import argparse
import collections
import json
import os
import textwrap
from pathlib import Path
from typing import Dict, List, Set

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """
    Config object that can be saved/loaded to/from a json file and provides IDE support
    by virtue of being represented as a python class.

    Usage pattern is to read in the configuration from file by dependency-injection
    at the start of any dependent functions and if modified should write the updated
    config back to the file.
    """
    NAMESPACE = ''  # one of 'start', 'stop' or 'reset'

    # top-level namespaces
    TOP_LEVEL = "top_level"
    START = "start"
    STOP = "stop"
    RESET = "reset"

    # package names
    ELECTRUMSV = "electrumsv"
    ELECTRUMX = "electrumx"
    ELECTRUMSV_INDEXER = "electrumsv_indexer"
    ELECTRUMSV_NODE = "electrumsv_node"

    subcmd_map: Dict[str, argparse.ArgumentParser] = {}  # cmd_name: ArgumentParser
    subcmd_raw_args_map: Dict[str, List[str]] = {}  # cmd_name: raw arguments
    subcmd_parsed_args_map = {}  # cmd_name: parsed arguments

    sdk_requirements_linux = Path(MODULE_DIR).joinpath("requirements").joinpath(
        "requirements-linux.txt")
    sdk_requirements_win32 = Path(MODULE_DIR).joinpath("requirements").joinpath(
        "requirements-win32.txt")

    # exclude plyvel from electrumx requirements.txt (windows workaround)
    sdk_requirements_electrumx = Path(MODULE_DIR).joinpath("requirements").joinpath(
        "requirements-electrumx.txt")

    depends_dir = Path(MODULE_DIR).parent.joinpath("sdk_depends")
    depends_dir_electrumsv = depends_dir.joinpath("electrumsv")
    depends_dir_electrumx = depends_dir.joinpath("electrumx")
    depends_dir_electrumx_data = depends_dir.joinpath("electrumx_data")

    depends_dir_electrumsv_req = depends_dir_electrumsv.joinpath(
        'contrib').joinpath('deterministic-build').joinpath('requirements.txt')
    depends_dir_electrumsv_req_bin = depends_dir_electrumsv.joinpath(
        'contrib').joinpath('deterministic-build').joinpath('requirements-binaries.txt')

    required_dependencies_set: Set[str] = set()

    run_scripts_dir = Path(MODULE_DIR).joinpath("run_scripts")

    @classmethod
    def from_dict(cls, config: Dict):
        config_instance = cls()
        for key, val in config.items():
            setattr(config_instance, key, val)
        return config_instance

    @classmethod
    def to_dict(cls,):
        config_dict = {}
        for key, val in cls.__dict__.items():
            config_dict[key] = val
        return config_dict


def load_config() -> Config:
    config_path = Path(MODULE_DIR).joinpath("config.json")
    with open(config_path.__str__(), "r") as f:
        config = json.loads(f.read())
    return Config.from_dict(config)


def save_config(config: Config):
    """completely overwrites config with new config json"""
    config_path = Path(MODULE_DIR).joinpath("config.json")
    with open(config_path.__str__(), "w") as f:
        f.write(json.dumps(config))

TOP_LEVEL_HELP_TEXT = textwrap.dedent("""
    electrumsv-sdk has a similar interface to systemctl with namespaces:
    - "start"
    - "stop"
    - "reset"

    The "start" command is the most feature-rich and launches servers as background 
    processes (see next):

    *********
    * start *
    *********

    examples:
    > electrumsv-sdk start --full-stack or
    > electrumsv-sdk start --esv-ex-node
    runs electrumsv + electrumx + electrumsv-node (both have equivalent effect)

    > electrumsv-sdk start --esv-idx-node
    will run electrumsv + electrumsv-indexer + electrumsv-node

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


    ********
    * stop *
    ********

    stops all running servers/spawned processes


    *********
    * reset *
    *********

    resets server state. e.g. 
    - bitcoin node state is reset back to genesis
    - electrumx state is reset back to genesis 
    - electrumsv RegTest wallet history is erased to match blockchain state


    """)