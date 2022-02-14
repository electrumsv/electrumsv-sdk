import os
import subprocess
import sys
from pathlib import Path

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

commands = [
    "electrumsv-sdk stop",
    "electrumsv-sdk --version",
    "electrumsv-sdk reset",
]

if os.getenv("LOCAL_DEV"):
    additional_commands = [
        "electrumsv-sdk install node",
        "electrumsv-sdk install simple_indexer",
        "electrumsv-sdk install reference_server",
        "electrumsv-sdk install electrumsv",
        "electrumsv-sdk install whatsonchain",
        "electrumsv-sdk start status_monitor",
        "electrumsv-sdk start node",
        "electrumsv-sdk start simple_indexer",
        "electrumsv-sdk start reference_server",
        "electrumsv-sdk start electrumsv",
        "electrumsv-sdk node generate 1",
        "electrumsv-sdk start whatsonchain",
    ]
else:
    additional_commands = [
        "electrumsv-sdk start --background status_monitor",
        "electrumsv-sdk start --background node",
        "electrumsv-sdk start --background simple_indexer",
        "electrumsv-sdk start --background reference_server",
        "electrumsv-sdk start --background electrumsv",
        "electrumsv-sdk node generate 1",
        "electrumsv-sdk start --background whatsonchain",
    ]

and_more_commands = [
    "electrumsv-sdk stop node",
    "electrumsv-sdk stop simple_indexer",
    "electrumsv-sdk stop reference_server",
    "electrumsv-sdk stop electrumsv",
    "electrumsv-sdk stop whatsonchain",

    "electrumsv-sdk reset --id=node1",
    "electrumsv-sdk reset --id=electrumsv1",
    f"{sys.executable} -m pylint --rcfile ../.pylintrc {Path(MODULE_DIR).parent.joinpath('electrumsv_sdk')}",
]

try:
    commands.extend(additional_commands)
    commands.extend(and_more_commands)
    for command in commands:
        subprocess.run(command, shell=True, check=True)
finally:
    subprocess.run("electrumsv-sdk stop", shell=True, check=True)
