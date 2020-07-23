import argparse
import json
import os
import textwrap
from pathlib import Path
from typing import Dict, List, Set
from os.path import expanduser

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Only electrumsv paths are saved to config.json so that 'reset' works on correct wallet."""
    NAMESPACE = ''  # 'start', 'stop' or 'reset'

    # namespaces
    TOP_LEVEL = "top_level"
    START = "start"
    STOP = "stop"
    RESET = "reset"
    NODE = "node"

    # package names
    ELECTRUMSV = "electrumsv"
    ELECTRUMX = "electrumx"
    ELECTRUMSV_INDEXER = "electrumsv_indexer"
    ELECTRUMSV_NODE = "electrumsv_node"

    subcmd_map: Dict[str, argparse.ArgumentParser] = {}  # cmd_name: ArgumentParser
    subcmd_raw_args_map: Dict[str, List[str]] = {}  # cmd_name: raw arguments
    subcmd_parsed_args_map = {}  # cmd_name: parsed arguments

    sdk_requirements_linux = Path(MODULE_DIR).parent.joinpath("requirements").joinpath(
        "requirements-linux.txt")
    sdk_requirements_win32 = Path(MODULE_DIR).parent.joinpath("requirements").joinpath(
        "requirements-win32.txt")

    # exclude plyvel from electrumx requirements.txt (windows workaround)
    sdk_requirements_electrumx = Path(MODULE_DIR).parent.joinpath("requirements").joinpath(
        "requirements-electrumx.txt")

    home = Path(expanduser("~"))
    electrumsv_sdk_data_dir = home.joinpath("ElectrumSV-SDK")
    depends_dir = electrumsv_sdk_data_dir.joinpath("sdk_depends")
    run_scripts_dir = electrumsv_sdk_data_dir.joinpath("run_scripts")
    proc_ids_path = run_scripts_dir.joinpath("proc_ids.json")

    # electrumsv paths are set dynamically at startup - see: set_electrumsv_path()
    electrumsv_dir = None
    electrumsv_data_dir = None
    electrumsv_regtest_dir = None
    electrumsv_regtest_config_dir = None
    electrumsv_regtest_wallets_dir = None
    electrumsv_requirements_path = None
    electrumsv_binary_requirements_path = None

    electrumx_dir = depends_dir.joinpath("electrumx")
    electrumx_data_dir = depends_dir.joinpath("electrumx_data")

    required_dependencies_set: Set[str] = set()

    node_args = None

    @classmethod
    def set_electrumsv_path(cls, electrumsv_dir: Path):
        """This is set dynamically at startup. It is *only persisted for purposes of the 'reset'
        command. The trade-off is that the electrumsv 'repo' will need to be specified anew every
        time the SDK 'start' command is run."""
        cls.electrumsv_dir = electrumsv_dir
        cls.electrumsv_data_dir = cls.electrumsv_dir.joinpath("electrum_sv_data")
        cls.electrumsv_regtest_dir = cls.electrumsv_data_dir.joinpath("regtest")
        cls.electrumsv_regtest_config_dir = cls.electrumsv_regtest_dir.joinpath("config")
        cls.electrumsv_regtest_wallets_dir = cls.electrumsv_regtest_dir.joinpath("wallets")
        cls.electrumsv_requirements_path = cls.electrumsv_dir.joinpath('contrib').joinpath(
            'deterministic-build').joinpath('requirements.txt')
        cls.electrumsv_binary_requirements_path = cls.electrumsv_dir.joinpath('contrib').joinpath(
            'deterministic-build').joinpath('requirements-binaries.txt')

    @classmethod
    def update_from_dict(cls, config: Dict):
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

    @classmethod
    def save_repo_paths(cls):
        """overwrites config.json"""
        config_path = Path(MODULE_DIR).joinpath("config.json")
        with open(config_path.__str__(), "w") as f:
            repo_paths = {}
            repo_paths['electrumsv_dir'] = cls.electrumsv_dir.__str__()
            f.write(json.dumps(repo_paths))

    @classmethod
    def load_repo_paths(cls) -> "Config":
        """loads state from config.json"""
        config_path = Path(MODULE_DIR).joinpath("config.json")
        with open(config_path.__str__(), "r") as f:
            config = json.loads(f.read())
            electrumsv_dir = config.get("electrumsv_dir")
            if electrumsv_dir:
                cls.set_electrumsv_path(Path(electrumsv_dir))
            else:
                cls.set_electrumsv_path(Path(cls.depends_dir.joinpath("electrumsv")))


TOP_LEVEL_HELP_TEXT = textwrap.dedent("""
    top-level
    =========
    electrumsv-sdk has four top-level namespaces (and works similarly to systemctl):
    - "start"
    - "stop"
    - "reset"
    - "node"

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

    """)
