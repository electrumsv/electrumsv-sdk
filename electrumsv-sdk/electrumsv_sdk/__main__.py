import logging
import sys
import platform

from electrumsv_sdk.app_state import AppState
from electrumsv_sdk.utils import create_if_not_exist

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(name)-24s %(message)s',
    level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger("main")

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
    app_state = AppState()
    create_if_not_exist(app_state.depends_dir.__str__())
    create_if_not_exist(app_state.run_scripts_dir.__str__())
    app_state.handle_first_ever_run()

    # Parse args
    app_state.arparser.setup_argparser()
    app_state.arparser.manual_argparsing(sys.argv)

    # Check & Install dependencies / or Configure state for 'Runners'
    app_state.install_handlers.handle_install()

    # Call Relevant 'Runner'
    if app_state.NAMESPACE == app_state.START:
        app_state.runners.start()

    if app_state.NAMESPACE == app_state.STOP:
        app_state.runners.stop()

    if app_state.NAMESPACE == app_state.RESET:
        app_state.runners.reset()

    if app_state.NAMESPACE == app_state.NODE:
        app_state.runners.node()

    if app_state.NAMESPACE == app_state.STATUS:
        app_state.runners.status()

if __name__ == "__main__":
    main()
