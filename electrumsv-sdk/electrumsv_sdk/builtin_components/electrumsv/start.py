import asyncio
import logging
import os
import sys

from electrumsv_node import electrumsv_node

from electrumsv_sdk.builtin_components.electrumx.start import is_electrumx_running
from electrumsv_sdk.utils import get_directory_name

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def init_electrumsv_wallet_dir(app_state):
    os.makedirs(app_state.electrumsv_data_dir.joinpath("regtest/wallets"), exist_ok=True)


def esv_check_node_and_electrumx_running():
    if not electrumsv_node.is_running():
        logger.debug("Electrumsv in RegTest mode requires a bitcoin node to be running... "
                     "failed to connect")
        sys.exit()

    is_running = asyncio.run(is_electrumx_running())
    if not is_running:
        logger.debug("Electrumsv in RegTest mode requires electrumx to be running... "
                     "failed to connect")
