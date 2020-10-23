import logging
import sys

from electrumsv_sdk.components import ComponentOptions
from electrumsv_sdk.argparsing import NameSpace
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
    app_state.handle_first_ever_run()

    # Parse args
    app_state.arparser.setup_argparser()
    app_state.arparser.manual_argparsing(sys.argv)
    app_state.handlers.handle_cli_args()

    # Call relevant entrypoint
    if app_state.NAMESPACE == NameSpace.START:
        app_state.controller.start(
            selected_component=app_state.selected_component,
            repo=app_state.global_cli_flags[ComponentOptions.REPO],
            component_id=app_state.global_cli_flags[ComponentOptions.ID],
            background=app_state.global_cli_flags[ComponentOptions.BACKGROUND],
            component_args=app_state.component_args,
        )  # -> install() -> start() ->
        # status_check() plugin
        # entrypoints

    if app_state.NAMESPACE == NameSpace.STOP:
        app_state.controller.stop(
            selected_component=app_state.selected_component,
            component_id=app_state.global_cli_flags[ComponentOptions.ID],
            background=app_state.global_cli_flags[ComponentOptions.BACKGROUND],
        )  # -> stop() entrypoint of plugin

    if app_state.NAMESPACE == NameSpace.RESET:
        app_state.controller.reset(
            selected_component=app_state.selected_component,
            component_id=app_state.global_cli_flags[ComponentOptions.ID],
            background=app_state.global_cli_flags[ComponentOptions.BACKGROUND],
        )  # -> reset() entrypoint of plugin

    # Special built-in execution pathway (not part of plugin system)
    if app_state.NAMESPACE == NameSpace.NODE:
        app_state.controller.node()

    # Http 'GET' request to status_monitor
    if app_state.NAMESPACE == NameSpace.STATUS:
        app_state.controller.status()


if __name__ == "__main__":
    main()
