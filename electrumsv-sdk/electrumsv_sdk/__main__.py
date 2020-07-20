import json
import subprocess
import sys
import platform
import time

from electrumsv_node import electrumsv_node

from electrumsv_sdk.config import Config
from .app import setup_argparser, manual_argparsing, startup
from .handlers import handle

def start():
    procs = startup()
    with open(Config.proc_ids_path, 'w') as f:
        f.write(json.dumps(procs))

def stop():
    with open(Config.proc_ids_path, 'r') as f:
        procs = json.loads(f.read())
    electrumsv_node.stop()

    if len(procs) != 0:
        for proc in procs:
            subprocess.run(f"taskkill.exe /PID {proc} /T /F")
    print("stack terminated")

def reset():
    pass


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
    procs = []
    try:
        print("ElectrumSV Software Development Kit")
        print(
            f"-Python version {sys.version_info.major}.{sys.version_info.minor}."
            f"{sys.version_info.micro}-{platform.architecture()[0]}"
        )
        print()

        setup_argparser()
        manual_argparsing(sys.argv)  # updates global 'Config.subcmd_parsed_args_map'
        handle()
        if Config.NAMESPACE == Config.START:
            start()

        if Config.NAMESPACE == Config.STOP:
            stop()

        if Config.NAMESPACE == Config.RESET:
            reset()
    except KeyboardInterrupt:
        electrumsv_node.stop()

        if len(procs) != 0:
            for proc in procs:
                subprocess.run(f"taskkill.exe /PID {proc.pid} /T /F")
        print("stack terminated")

if __name__ == "__main__":
    main()