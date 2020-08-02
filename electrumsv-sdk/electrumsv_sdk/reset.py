import logging
import os
import shutil
from electrumsv_node import electrumsv_node

from .utils import create_if_not_exist, topup_wallet, create_wallet, delete_wallet

logger = logging.getLogger("main")
orm_logger = logging.getLogger('peewee')
orm_logger.setLevel(logging.WARNING)


class Resetters:

    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
    
    def reset_node(self):
        electrumsv_node.reset()
        logger.debug("reset of RegTest bitcoin daemon completed successfully.")

    def reset_electrumx(self):
        logger.debug("resetting state of RegTest electrumx server...")
        electrumx_data_dir = self.app_state.electrumx_data_dir
        if electrumx_data_dir.exists():
            shutil.rmtree(electrumx_data_dir.__str__())
            os.mkdir(electrumx_data_dir.__str__())
        else:
            create_if_not_exist(electrumx_data_dir)
        logger.debug("reset of RegTest electrumx server completed successfully.")

    def reset_electrumsv_wallet(self):
        """depends on having node and electrumx already running"""
        logger.debug("resetting state of RegTest electrumsv server...")
        delete_wallet(self.app_state)
        create_wallet()
        topup_wallet()
        logger.debug("reset of RegTest electrumsv wallet completed successfully")
