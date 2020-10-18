import logging
import os

from electrumsv_sdk.utils import get_directory_name

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def is_offline_cli_mode(app_state):
    if len(app_state.component_args) != 0:
        if app_state.component_args[0] in ['create_wallet', 'create_account', '--help']:
            return True
    return False


def init_electrumsv_wallet_dir(app_state):
    os.makedirs(app_state.component_datadir.joinpath("regtest/wallets"), exist_ok=True)
