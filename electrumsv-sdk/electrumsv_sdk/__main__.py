import logging
import os
import platform
import sys

from electrumsv_sdk.app_state import AppState

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(name)-24s %(message)s',
    level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger("main")
logger_requests = logging.getLogger("urllib3").setLevel(logging.WARNING)

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
        f"-Python version {platform.python_version()}-{platform.architecture()[0]}"
    )
    print()
    app_state = AppState()
    os.makedirs(app_state.depends_dir, exist_ok=True)
    os.makedirs(app_state.run_scripts_dir, exist_ok=True)
    app_state.handle_first_ever_run()

    # Parse args
    app_state.arparser.setup_argparser()
    app_state.arparser.manual_argparsing(sys.argv)

    # Check & Install dependencies / or Configure state for 'Runners'
    app_state.handlers.handle_install()

    # Call Relevant 'Runner'
    if app_state.NAMESPACE == app_state.START:
        app_state.controller.start()

    if app_state.NAMESPACE == app_state.STOP:
        app_state.controller.stop()

    if app_state.NAMESPACE == app_state.RESET:
        app_state.controller.reset()

    if app_state.NAMESPACE == app_state.NODE:
        app_state.controller.node()

    if app_state.NAMESPACE == app_state.STATUS:
        app_state.controller.status()

if __name__ == "__main__":
    main()
