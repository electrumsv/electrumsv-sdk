"""This acts as a kind of middleware - which has now been whittled down to only providing
logging information"""

import logging
import platform

from .constants import NameSpace
from .config import Config, ParsedArgs
from .utils import read_sdk_version

logger = logging.getLogger("validate-cli-args")


class ValidateCliArgs:
    """Called via ArgParser.validate_cli_args"""

    def __init__(self, config: Config):
        self.config = config

    # ----- MAIN ARGUMENT HANDLERS ----- #
    def handle_top_level_args(self, parsed_args: ParsedArgs) -> None:
        if not self.config.namespace == NameSpace.TOP_LEVEL:
            return

        if parsed_args.version:
            logger.info("ElectrumSV Software Development Kit")
            logger.info(f"Python version {platform.python_version()}-{platform.architecture()[0]}")
            logger.info(f"SDK version {read_sdk_version()}")

    def handle_install_args(self, parsed_args: ParsedArgs) -> None:
        if not self.config.namespace == NameSpace.INSTALL:
            return

        # logging
        if parsed_args.id != "":
            logger.debug(f"id flag={parsed_args.id}")
        if parsed_args.repo != "":
            logger.debug(f"repo flag={parsed_args.repo}")
        if parsed_args.branch != "":
            logger.debug(f"branch flag={parsed_args.branch}")

    def handle_start_args(self, parsed_args: ParsedArgs) -> None:
        if not self.config.namespace == NameSpace.START:
            return

        # logging
        if parsed_args.new:
            logger.debug("new flag=set")
        if parsed_args.gui:
            logger.debug("gui flag=set")
        if parsed_args.id != "":
            logger.debug(f"id flag={parsed_args.id}")
        if parsed_args.repo != "":
            logger.debug(f"repo flag={parsed_args.repo}")
        if parsed_args.branch != "":
            logger.debug(f"branch flag={parsed_args.branch}")

    def handle_stop_args(self, parsed_args: ParsedArgs) -> None:
        """takes no arguments"""
        if not self.config.namespace == NameSpace.STOP:
            return

        # logging
        if parsed_args.id != "":
            logger.debug(f"id flag={parsed_args.id}")

    def handle_reset_args(self, parsed_args: ParsedArgs) -> None:
        """takes no arguments"""
        if not self.config.namespace == NameSpace.RESET:
            return

        # logging
        if parsed_args.id != "":
            logger.debug(f"id flag={parsed_args.id}")
        if parsed_args.repo != "":
            logger.debug(f"repo flag={parsed_args.repo}")

    def handle_status_args(self, _parsed_args: ParsedArgs) -> None:
        return

    def handle_config_args(self, _parsed_args: ParsedArgs) -> None:
        return
