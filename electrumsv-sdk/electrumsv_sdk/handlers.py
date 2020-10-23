import logging
import platform
import sys

from .argparsing import NameSpace
from .utils import read_sdk_version
from .components import ComponentOptions

logger = logging.getLogger("install-handlers")


class Handlers:

    def __init__(self, app_state: "AppState"):
        self.app_state = app_state

    def validate_flags(self, parsed_args):
        flags_selected = [flag for flag, value in parsed_args.__dict__.items()
                          if value not in {"", None, False}]
        if all(flag in {'new', 'gui', 'id', 'branch', 'repo', 'background'} for flag in
               parsed_args.__dict__):
            return True, flags_selected
        return False, flags_selected

    # ----- MAIN ARGUMENT HANDLERS ----- #
    def handle_top_level_args(self, parsed_args):
        if not self.app_state.NAMESPACE == NameSpace.TOP_LEVEL:
            return

        if parsed_args.version:
            logger.info("ElectrumSV Software Development Kit")
            logger.info(f"Python version {platform.python_version()}-{platform.architecture()[0]}")
            logger.info(f"SDK version {read_sdk_version()}")

    def handle_start_args(self, parsed_args):
        if not self.app_state.NAMESPACE == NameSpace.START:
            return

        valid_input, flags = self.validate_flags(parsed_args)
        if not valid_input:
            logger.info(f"valid flags include: ['--new', '--gui', '--id', --branch, --repo]. You "
                  f"selected '{flags}'")
            return

        self.app_state.global_cli_flags[ComponentOptions.NEW] = parsed_args.new
        self.app_state.global_cli_flags[ComponentOptions.GUI] = parsed_args.gui
        self.app_state.global_cli_flags[ComponentOptions.BACKGROUND] = parsed_args.background
        self.app_state.global_cli_flags[ComponentOptions.ID] = id = parsed_args.id
        self.app_state.global_cli_flags[ComponentOptions.REPO] = repo = parsed_args.repo
        self.app_state.global_cli_flags[ComponentOptions.BRANCH] = branch = parsed_args.branch

        def has_startup_flags():
            return parsed_args.new or parsed_args.gui

        if has_startup_flags():
            if not self.app_state.selected_component:
                logger.error("must select a component type when specifying --new or --gui flags")
                sys.exit(1)

        # logging
        if parsed_args.new:
            logger.debug("new flag=set")
        if parsed_args.gui:
            logger.debug("gui flag=set")
        if id != "":
            logger.debug(f"id flag={parsed_args.id}")
        if repo != "":
            logger.debug(f"repo flag={self.app_state.global_cli_flags[ComponentOptions.REPO]}")
        if branch != "":
            logger.debug(f"branch flag={parsed_args.branch}")

    def handle_stop_args(self, parsed_args):
        """takes no arguments"""
        if not self.app_state.NAMESPACE == NameSpace.STOP:
            return

        self.app_state.global_cli_flags[ComponentOptions.ID] = id = parsed_args.id
        component_name = self.app_state.selected_component
        if id and component_name:
            logger.error("stop command cannot handle both --id flag and <component_type>. Please "
                         "select one or the other.")
            sys.exit(1)

        # logging
        if id != "":
            logger.debug(f"id flag={parsed_args.id}")

    def handle_reset_args(self, parsed_args):
        """takes no arguments"""
        if not self.app_state.NAMESPACE == NameSpace.RESET:
            return

        self.app_state.global_cli_flags[ComponentOptions.ID] = id = parsed_args.id
        self.app_state.global_cli_flags[ComponentOptions.REPO] = repo = parsed_args.repo

        # logging
        if id != "":
            logger.debug(f"id flag={parsed_args.id}")
        if repo != "":
            logger.debug(f"repo flag={self.app_state.global_cli_flags[ComponentOptions.REPO]}")

    def handle_node_args(self, parsed_args):
        """parsed_args are actually raw args. feeds runners.node() via Config.node_args"""
        if not self.app_state.NAMESPACE == NameSpace.NODE:
            return
        self.app_state.node_args = parsed_args

    def handle_status_args(self, _parsed_args):
        return

    # ----- HANDLERS ENTRY POINT ----- #

    def handle_cli_args(self):
        """calls the appropriate handler for the argparsing.NameSpace"""
        for namespace, parsed_args in self.app_state.parser_parsed_args_map.items():
            if self.app_state.NAMESPACE == namespace:
                func = getattr(self, "handle_" + namespace + "_args")
                func(parsed_args)
