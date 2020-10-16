import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

from electrumsv_node import electrumsv_node

from .components import ComponentOptions, ComponentStore, ComponentName

logger = logging.getLogger("resetters")
orm_logger = logging.getLogger("peewee")
orm_logger.setLevel(logging.WARNING)


class Resetters:
    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.component_store = ComponentStore(self.app_state)

    def normalize_wallet_name(self, wallet_name: str):
        if wallet_name is not None:
            if not wallet_name.endswith(".sqlite"):
                wallet_name += ".sqlite"
        else:
            wallet_name = "worker1.sqlite"
        return wallet_name

    def create_wallet(self, wallet_name: str = None):
        try:
            logger.debug("Creating wallet...")
            wallet_name = self.normalize_wallet_name(wallet_name)
            wallet_path = self.app_state.electrumsv_data_dir\
                .joinpath(f"regtest/wallets/{wallet_name}")
            password = "test"

            command = (
                f"electrumsv-sdk start --background --repo"
                f"={self.app_state.start_options[ComponentOptions.REPO]} "
                f"electrumsv create_wallet --wallet {wallet_path} "
                f"--walletpassword {password} --portable --no-password-check")

            subprocess.run(command, shell=True, check=True)
            logger.debug(f"New wallet created at : {wallet_path} ")
        except Exception as e:
            logger.exception("unexpected problem creating new wallet")
            raise

    def delete_wallet(self, wallet_name: str = None):
        wallet_name = self.normalize_wallet_name(wallet_name)
        esv_wallet_db_directory = self.app_state.electrumsv_data_dir.joinpath("regtest/wallets")
        os.makedirs(esv_wallet_db_directory, exist_ok=True)

        try:
            time.sleep(1)
            logger.debug("Deleting wallet...")
            logger.debug(
                "Wallet directory before: %s", os.listdir(esv_wallet_db_directory),
            )
            file_names = [
                wallet_name,
                wallet_name + "-shm",
                wallet_name + "-wal",
            ]
            for file_name in file_names:
                file_path = esv_wallet_db_directory.joinpath(file_name)
                if Path.exists(file_path):
                    os.remove(file_path)
            logger.debug(
                "Wallet directory after: %s", os.listdir(esv_wallet_db_directory),
            )
        except Exception as e:
            logger.exception(e)
            raise

    def reset_node(self):
        electrumsv_node.reset()
        logger.debug("Reset of RegTest bitcoin daemon completed successfully.")

    def reset_electrumx(self):
        logger.debug("Resetting state of RegTest electrumx server...")
        electrumx_data_dir = self.app_state.electrumx_data_dir
        if electrumx_data_dir.exists():
            shutil.rmtree(electrumx_data_dir)
            os.mkdir(electrumx_data_dir)
        else:
            os.makedirs(electrumx_data_dir, exist_ok=True)
        logger.debug("Reset of RegTest electrumx server completed successfully.")

    def reset_electrumsv_wallet(self, component_id=None):
        """depends on having node and electrumx already running"""
        logger.debug("Resetting state of RegTest electrumsv server...")
        if component_id is None:
            logger.warning("Note: No --id flag is specified. Therefore the default 'electrumsv1' "
                "instance will be reset.")
        self.delete_wallet()
        self.create_wallet()
        logger.debug("Reset of RegTest electrumsv wallet completed successfully")

    def reset_component(self, component_name: ComponentName, component_id=None):
        if ComponentName.NODE == component_name:
            self.reset_node()

        if ComponentName.ELECTRUMX == component_name:
            self.reset_electrumx()

        if ComponentName.ELECTRUMSV == component_name:
            self.reset_electrumsv_wallet(component_id)
            if component_id:
                self.app_state.run_command_current_shell(f"electrumsv-sdk stop --id={component_id}")
            else:
                self.app_state.run_command_current_shell(f"electrumsv-sdk stop electrumsv")

        if ComponentName.INDEXER == component_name:
            logger.error("resetting indexer is not supported at this time...")

        if ComponentName.STATUS_MONITOR == component_name:
            logger.error("resetting the status monitor is not supported at this time...")
