import logging
import platform
import sys

from .utils import read_sdk_version
from .components import ComponentName, ComponentOptions

logger = logging.getLogger("install-handlers")


class Handlers:
    """The handlers associated with the 'start' command check to see what is already installed
    compared to the cli inputs and if not installed and it is required will proceed to install
    the missing dependency.

    NOTE: if there is a conflict (e.g. installing a remote forked github repo would over-write
    the existing install of the official github repo) then a ".bak: backup will be created for
    the existing version of the repo.

    No arg ("") will default to the 'official' github repo.

    All handlers are called no matter what and args are fed to them - if any. But if their
    relevant namespace is not 'active' (i.e. 'start', 'stop' or 'reset') then they do not action
    anything -> return
    """

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
        if not self.app_state.NAMESPACE == self.app_state.TOP_LEVEL:
            return

        if parsed_args.version:
            logger.info("ElectrumSV Software Development Kit")
            logger.info(f"Python version {platform.python_version()}-{platform.architecture()[0]}")
            logger.info(f"SDK version {read_sdk_version()}")

        # print("TOP LEVEL ARGS HANDLER")
        # print(f"parsed_args={parsed_args}")

    def handle_start_args(self, parsed_args):
        """the top-level arguments (preceeding any subcommand) cover two main functionalities:
        1) mode of operation:
        --full-stack OR --node OR --ex-node OR --esv-ex-node OR --esv-idx-node
        2) extension 3rd party applications launched against the rest of the stack:
        --extapp EXTAPP_PATH1 --extapp EXTAPP_PATH2 --extapp EXTAPP_PATH3 ...

        For (1), a set of required dependencies is gathered and is then satisfied
        by the handlers below for the given dependency.
        For (2), extension app support is not supported yet (but will allow for any non-python
        servers to be run (e.g. a localhost blockexplorer perhaps)
        """
        if not self.app_state.NAMESPACE == self.app_state.START:
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
            return parsed_args.new or parsed_args.gui or id != "" or repo != "" or branch != ""

        if has_startup_flags():
            if len(self.app_state.selected_start_component) == 0:
                logger.error("must select a component type when specifying startup flags")
                sys.exit()

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
        if not self.app_state.NAMESPACE == self.app_state.STOP:
            return

        self.app_state.global_cli_flags[ComponentOptions.ID] = id = parsed_args.id
        component_name = self.app_state.selected_stop_component
        if id and component_name:
            logger.error("stop command cannot handle both --id flag and <component_type>. Please "
                         "select one or the other.")
            sys.exit(1)

        # logging
        if id != "":
            logger.debug(f"id flag={parsed_args.id}")

    def handle_reset_args(self, parsed_args):
        """takes no arguments"""
        if not self.app_state.NAMESPACE == self.app_state.RESET:
            return

        self.app_state.global_cli_flags[ComponentOptions.ID] = id = parsed_args.id
        self.app_state.global_cli_flags[ComponentOptions.REPO] = repo = parsed_args.repo
        self.app_state.global_cli_flags[ComponentOptions.BRANCH] = branch = parsed_args.branch

        # logging
        if id != "":
            logger.debug(f"id flag={parsed_args.id}")
        if repo != "":
            logger.debug(f"repo flag={self.app_state.global_cli_flags[ComponentOptions.REPO]}")
        if branch != "":
            logger.debug(f"branch flag={parsed_args.branch}")

    def handle_node_args(self, parsed_args):
        """parsed_args are actually raw args. feeds runners.node() via Config.node_args"""
        if not self.app_state.NAMESPACE == ComponentName.NODE:
            return
        self.app_state.node_args = parsed_args

    def handle_status_args(self, _parsed_args):
        """takes no arguments"""
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

    def handle_whatsonchain_args(self, _parsed_args):
        """takes no arguments"""
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.WHATSONCHAIN == self.app_state.selected_start_component:
            return

    def handle_electrumsv_args(self, _parsed_args):
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.ELECTRUMSV == self.app_state.selected_start_component:
            return

    def handle_electrumx_args(self, _parsed_args):
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.ELECTRUMX == self.app_state.selected_start_component:
            return

    def handle_electrumsv_node_args(self, _parsed_args):
        """not to be confused with node namespace:
        > electrumsv-sdk node <rpc commands>
        This is for the subcommand of the 'start' namespace:
        > 'electrumsv-sdk start electrumsv_node repo=<repo> branch=<branch>'
        """
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.NODE == self.app_state.selected_start_component:
            return

    def handle_indexer_args(self, _parsed_args):
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.INDEXER == self.app_state.selected_start_component:
            return

    def handle_status_monitor_args(self, _parsed_args):
        return

    # ----- HANDLERS ENTRY POINT ----- #

    def handle_cli_args(self):
        for cmd, parsed_args in self.app_state.subcmd_parsed_args_map.items():
            func = getattr(self, "handle_" + cmd + "_args")
            func(parsed_args)
