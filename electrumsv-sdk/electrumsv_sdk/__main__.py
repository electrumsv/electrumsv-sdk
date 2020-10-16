import logging
import os
import sys

from electrumsv_sdk.app_state import AppState  # pylint: disable=E0401

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
    app_state = AppState()
    os.makedirs(app_state.depends_dir, exist_ok=True)
    os.makedirs(app_state.run_scripts_dir, exist_ok=True)
    app_state.handle_first_ever_run()

    # Parse args
    app_state.arparser.setup_argparser()
    app_state.arparser.manual_argparsing(sys.argv)

    # Check & Install dependencies / or Configure state for main execution pathway
    # indirectly calls the 'install()' entrypoint for the component with config based on cli args
    app_state.handlers.handle_cli_args()

    # Call Relevant 'Runner'
    if app_state.NAMESPACE == app_state.START:
        app_state.controller.start()  # -> install() + start() entrypoint of plugin

    if app_state.NAMESPACE == app_state.STOP:
        app_state.controller.stop()  # -> stop() entrypoint of plugin

    if app_state.NAMESPACE == app_state.RESET:
        app_state.controller.reset()  # -> reset() entrypoint of plugin

    # Special built-in execution pathway (not part of plugin system)
    if app_state.NAMESPACE == app_state.NODE:
        app_state.controller.node()

    if app_state.NAMESPACE == app_state.STATUS:
        app_state.controller.status()


if __name__ == "__main__":
    main()
