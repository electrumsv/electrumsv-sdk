import json
import logging
import os
import shutil
import stat
import sys
import platform

from electrumsv_node import electrumsv_node
from electrumsv_sdk.app_state import AppState
from electrumsv_sdk.install_tools import create_if_not_exist
from electrumsv_sdk.runners import start, stop, reset, node, status
from electrumsv_sdk.argparsing import setup_argparser, manual_argparsing
from electrumsv_sdk.install_handlers import handle_install

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(name)-24s %(message)s',
    level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger("main")


def purge_prev_installs_if_exist():
    def remove_readonly(func, path, excinfo):  # .git is read-only
        os.chmod(path, stat.S_IWRITE)
        func(path)

    if AppState.depends_dir.exists():
        shutil.rmtree(AppState.depends_dir.__str__(), onerror=remove_readonly)
        create_if_not_exist(AppState.depends_dir.__str__())
    if AppState.run_scripts_dir.exists():
        shutil.rmtree(AppState.run_scripts_dir.__str__(), onerror=remove_readonly)
        create_if_not_exist(AppState.run_scripts_dir.__str__())

def handle_first_ever_run():
    """nukes previously installed dependencies and .bat/.sh scripts for the first ever run of the
    electrumsv-sdk."""
    try:
        with open(AppState.electrumsv_sdk_config_path.__str__(), 'r') as f:
            config = json.loads(f.read())
    except FileNotFoundError:
        with open(AppState.electrumsv_sdk_config_path.__str__(), 'w') as f:
            config = {"is_first_run": True}
            f.write(json.dumps(config, indent=4))

    if config.get("is_first_run") or config.get("is_first_run") is None:
        logger.debug("running SDK for the first time. please wait for configuration to complete...")
        logger.debug("purging previous server installations (if any)...")
        purge_prev_installs_if_exist()
        with open(AppState.electrumsv_sdk_config_path.__str__(), 'w') as f:
            config = {"is_first_run": False}
            f.write(json.dumps(config, indent=4))
        logger.debug("purging completed successfully")

        electrumsv_node.reset()

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

    create_if_not_exist(AppState.depends_dir.__str__())
    create_if_not_exist(AppState.run_scripts_dir.__str__())
    handle_first_ever_run()

    # Parse args
    setup_argparser()
    manual_argparsing(sys.argv)

    # Handle & Install dependencies / or Configure state for 'Runner'
    handle_install()

    # Call Relevant 'Runner'
    if AppState.NAMESPACE == AppState.START:
        start()

    if AppState.NAMESPACE == AppState.STOP:
        stop()

    if AppState.NAMESPACE == AppState.RESET:
        reset()

    if AppState.NAMESPACE == AppState.NODE:
        node()

    if AppState.NAMESPACE == AppState.STATUS:
        status()

if __name__ == "__main__":
    main()
