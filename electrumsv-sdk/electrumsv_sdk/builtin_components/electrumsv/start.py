import logging
import os
import time

from electrumsv_sdk.utils import get_directory_name

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def is_offline_cli_mode(app_state):
    if len(app_state.component_args) != 0:
        if app_state.component_args[0] in ['create_wallet', 'create_account', '--help']:
            return True
    return False


def wallet_db_exists(app_state):
    if os.path.exists(app_state.component_datadir.joinpath("regtest/wallets/worker1.sqlite")):
        return True
    time.sleep(3)  # takes a short time for .sqlite file to become visible
    if os.path.exists(app_state.component_datadir.joinpath("regtest/wallets/worker1.sqlite")):
        return True
    return False

