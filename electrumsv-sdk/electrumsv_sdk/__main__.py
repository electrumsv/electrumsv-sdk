import sys
import platform

from electrumsv_sdk.config import Config
from electrumsv_sdk.runners import start, stop, reset
from electrumsv_sdk.argparsing import setup_argparser, manual_argparsing
from electrumsv_sdk.handlers import handle


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

    setup_argparser()
    manual_argparsing(sys.argv)
    handle()
    if Config.NAMESPACE == Config.START:
        start()

    if Config.NAMESPACE == Config.STOP:
        stop()

    if Config.NAMESPACE == Config.RESET:
        reset()

if __name__ == "__main__":
    main()
