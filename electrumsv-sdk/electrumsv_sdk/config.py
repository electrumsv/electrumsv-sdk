import argparse
import collections
import json
import os
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

    # package names
    ELECTRUMSV_SDK = "electrumsv_sdk"
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
