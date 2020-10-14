import subprocess

commands = [
    "electrumsv-sdk start --background node",
    "electrumsv-sdk start --background electrumx",
    "electrumsv-sdk start --background electrumsv",
    "electrumsv-sdk node generate 1",
    "electrumsv-sdk start --background whatsonchain",

    "electrumsv-sdk stop node",
    "electrumsv-sdk stop electrumx",
    "electrumsv-sdk stop electrumsv",
    "electrumsv-sdk stop whatsonchain",

    "electrumsv-sdk reset",

    "electrumsv-sdk reset --id=node1"
    "electrumsv-sdk"
    "reset --id=electrumx1"
    "electrumsv-sdk"
    "reset --id=electrumsv1"
]

try:
    for command in commands:
        subprocess.run(command, shell=True, check=True)
finally:
    subprocess.run("electrumsv-sdk stop", shell=True, check=True)

