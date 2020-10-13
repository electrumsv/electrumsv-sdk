import logging
import sys

from .components import ComponentName, ComponentOptions
from .install_tools import InstallTools
from .installers import Installers

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
        self.install_tools = InstallTools(app_state)
        self.app_state = app_state
        self.installer = Installers(self.app_state)

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

        self.app_state.start_options[ComponentOptions.NEW] = parsed_args.new
        self.app_state.start_options[ComponentOptions.GUI] = parsed_args.gui
        self.app_state.start_options[ComponentOptions.BACKGROUND] = parsed_args.background
        self.app_state.start_options[ComponentOptions.ID] = id = parsed_args.id
        self.app_state.start_options[ComponentOptions.REPO] = repo = parsed_args.repo
        self.app_state.start_options[ComponentOptions.BRANCH] = branch = parsed_args.branch

        def has_startup_flags():
            return parsed_args.new or parsed_args.gui or id != "" or repo != "" or branch != ""

        if has_startup_flags():
            if len(self.app_state.start_set) == 0:
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
            logger.debug(f"repo flag={self.app_state.start_options[ComponentOptions.REPO]}")

        if branch != "":
            logger.debug(f"branch flag={parsed_args.branch}")

    def handle_stop_args(self, _parsed_args):
        """takes no arguments"""
        if not self.app_state.NAMESPACE == self.app_state.STOP:
            return

    def handle_reset_args(self, parsed_args):
        """takes no arguments"""
        if not self.app_state.NAMESPACE == self.app_state.RESET:
            return

        self.app_state.start_options[ComponentOptions.ID] = id = parsed_args.id
        self.app_state.start_options[ComponentOptions.REPO] = repo = parsed_args.repo
        self.app_state.start_options[ComponentOptions.BRANCH] = branch = parsed_args.branch

        # logging
        if id != "":
            logger.debug(f"id flag={parsed_args.id}")

        if repo != "":
            logger.debug(f"repo flag={self.app_state.start_options[ComponentOptions.REPO]}")

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

        self.installer.status_monitor()

    def handle_whatsonchain_args(self, _parsed_args):
        """takes no arguments"""
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.WHATSONCHAIN in self.app_state.start_set and \
                len(self.app_state.start_set) != 0:
            return

        self.installer.whatsonchain()

    def handle_electrumsv_args(self, _parsed_args):
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.ELECTRUMSV in self.app_state.start_set and \
                len(self.app_state.start_set) != 0:
            return

        self.installer.electrumsv()

    def handle_electrumx_args(self, _parsed_args):
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.ELECTRUMX in self.app_state.start_set and \
                len(self.app_state.start_set) != 0:
            return

        self.installer.electrumx()

    def handle_electrumsv_node_args(self, _parsed_args):
        """not to be confused with node namespace:
        > electrumsv-sdk node <rpc commands>
        This is for the subcommand of the 'start' namespace:
        > 'electrumsv-sdk start electrumsv_node repo=<repo> branch=<branch>'
        """
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.NODE in self.app_state.start_set and \
                len(self.app_state.start_set) != 0:
            return

        self.app_state.installers.node()

    def handle_indexer_args(self, _parsed_args):
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.INDEXER in self.app_state.start_set:
            return

        self.app_state.installers.indexer()

    def handle_status_monitor_args(self, _parsed_args):
        return

    # ----- HANDLERS ENTRY POINT ----- #

    def handle_install(self):
        for cmd, parsed_args in self.app_state.subcmd_parsed_args_map.items():
            func = getattr(self, "handle_" + cmd + "_args")
            func(parsed_args)
