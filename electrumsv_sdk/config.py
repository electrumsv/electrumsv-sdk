import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """
    Config object that can be saved/loaded to/from a json file and provides IDE support
    by virtue of being represented as a python class.

    Usage pattern is to read in the configuration from file by dependency-injection
    at the start of any dependent functions and if modified should write the updated
    config back to the file.
    """
    subcmd_map: Dict[str, argparse.ArgumentParser] = {}  # cmd_name: ArgumentParser
    subcmd_raw_args_map: Dict[str, List[str]] = {}  # cmd_name: raw arguments
    subcmd_parsed_args_map = {}  # cmd_name: parsed arguments

    depends_dir = Path(MODULE_DIR).joinpath("electrumsv-sdk").joinpath("sdk_depends")
    depends_dir_electrumx = (Path(MODULE_DIR).joinpath("electrumsv-sdk").joinpath("electrumx"))
    depends_dir_electrumx_data = (Path(MODULE_DIR).joinpath("electrumsv-sdk")
        .joinpath("electrumx_data"))

    @classmethod
    def from_dict(cls, config: Dict):
        config_instance = cls()
        for key, val in config.items():
            setattr(config_instance, key, val)
        return config_instance


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
