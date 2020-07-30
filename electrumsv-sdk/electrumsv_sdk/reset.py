import json
import logging
import os
import shutil
import time
from pathlib import Path

import requests
from electrumsv_node import electrumsv_node
from electrumsv_sdk.utils import create_if_not_exist

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

    def delete_wallet(self):
        esv_wallet_db_directory = self.app_state.electrumsv_regtest_wallets_dir
        create_if_not_exist(esv_wallet_db_directory.__str__())

        try:
            time.sleep(1)
            logger.debug("deleting wallet...")
            logger.debug(
                "wallet directory before: %s",
                os.listdir(esv_wallet_db_directory.__str__()),

            )
            wallet_name = "worker1"
            file_names = [
                wallet_name + ".sqlite",
                wallet_name + ".sqlite-shm",
                wallet_name + ".sqlite-wal",
            ]
            for file_name in file_names:
                file_path = esv_wallet_db_directory.joinpath(file_name)
                if Path.exists(file_path):
                    os.remove(file_path)
            logger.debug(
                "wallet directory after: %s",
                os.listdir(esv_wallet_db_directory.__str__()),
            )
        except Exception as e:
            logger.exception(e)
        else:
            return

    def create_wallet(self):
        try:
            logger.debug("creating wallet...")
            wallet_name = "worker1"
            url = (
                f"http://127.0.0.1:9999/v1/regtest/dapp/wallets/"
                f"{wallet_name}.sqlite/create_new_wallet"
            )
            payload = {"password": "test"}
            response = requests.post(url, data=json.dumps(payload))
            response.raise_for_status()
            logger.debug(
                f"new wallet created in {response.json()['value']['new_wallet']}"
            )
        except Exception as e:
            logger.exception(e)

    def topup_wallet(self):
        logger.debug("topping up wallet...")
        payload = json.dumps({"jsonrpc": "2.0", "method": "sendtoaddress",
            "params": ["mwv1WZTsrtKf3S9mRQABEeMaNefLbQbKpg", 25], "id": 0, })
        result = requests.post("http://rpcuser:rpcpassword@127.0.0.1:18332", data=payload)
        result.raise_for_status()
        logger.debug(result.json())
        logger.debug(f"topped up wallet with 25 coins")

    def reset_electrumsv_wallet(self):
        """depends on having node and electrumx already running"""
        logger.debug("resetting state of RegTest electrumsv server...")
        self.delete_wallet()
        self.create_wallet()
        self.topup_wallet()
        logger.debug("reset of RegTest electrumsv wallet completed successfully")
