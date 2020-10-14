import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from electrumsv_node import electrumsv_node

from .stoppers import Stoppers
from .components import ComponentOptions, ComponentStore, ComponentName
from .installers import Installers
from .starters import Starters

logger = logging.getLogger("resetters")
orm_logger = logging.getLogger("peewee")
orm_logger.setLevel(logging.WARNING)


class Resetters:
    def __init__(self, app_state: "AppState"):
        self.app_state = app_state
        self.starters = Starters(self.app_state)
        self.stoppers = Stoppers(self.app_state)
        self.installers = Installers(self.app_state)
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
            wallet_path = self.app_state.electrumsv_regtest_wallets_dir.joinpath(wallet_name)
            password = "test"

            command = (
                f"electrumsv-sdk start "
                f"--repo={self.app_state.start_options[ComponentOptions.REPO]} "
                f"electrumsv create_wallet --wallet {wallet_path} "
                f"--walletpassword {password} --portable --no-password-check")

            subprocess.run(command, shell=True, check=True)
            logger.debug(f"New wallet created at : {wallet_path} ")
        except Exception as e:
            logger.exception("unexpected problem creating new wallet")

    def delete_wallet(self, wallet_name: str = None):
        wallet_name = self.normalize_wallet_name(wallet_name)
        esv_wallet_db_directory = self.app_state.electrumsv_regtest_wallets_dir
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
        else:
            return

    def reset_node(self):
        electrumsv_node.reset()
        logger.debug("Reset of RegTest bitcoin daemon completed successfully.")

    def reset_electrumx(self):
        logger.debug("Resetting state of RegTest electrumx server...")
        repo = self.app_state.start_options[ComponentOptions.REPO]
        branch = self.app_state.start_options[ComponentOptions.BRANCH]
        self.installers.configure_paths_and_maps_electrumx(repo, branch)

        electrumx_data_dir = self.app_state.electrumx_data_dir
        if electrumx_data_dir.exists():
            shutil.rmtree(electrumx_data_dir)
            os.mkdir(electrumx_data_dir)
        else:
            os.makedirs(electrumx_data_dir, exist_ok=True)
        logger.debug("Reset of RegTest electrumx server completed successfully.")

    def reset_electrumsv_wallet(self, component_id=None):
        """depends on having node and electrumx already running"""
        repo = self.app_state.start_options[ComponentOptions.REPO]
        branch = self.app_state.start_options[ComponentOptions.BRANCH]
        self.app_state.installers.configure_paths_and_maps_electrumsv(repo, branch)
        logger.debug("Resetting state of RegTest electrumsv server...")
        if component_id is None:
            logger.warning("Note: No --id flag is specified. Therefore the default 'electrumsv1' "
                "instance will be reset.")
        self.delete_wallet()
        self.create_wallet()
        logger.debug("Reset of RegTest electrumsv wallet completed successfully")

    def reset_component_by_id(self, component_id):
        if self.app_state.start_options[ComponentOptions.ID] != "":
            if len(self.app_state.reset_set) != 0:
                logger.debug(f"The '--id' flag is specified "
                             f"- ignoring the component type(s) {self.app_state.reset_set}")

        component_data = self.component_store.component_status_data_by_id(component_id)
        component_name = component_data.get('component_type')
        if component_data == {}:
            sys.exit(1)

        if component_data.get('component_type') == ComponentName.NODE:
            logger.debug(f"There is only one 'id' for this component type - resetting the "
                         f"default node id={component_id}")
            self.reset_node()

        elif component_data.get('component_type') == ComponentName.ELECTRUMX:
            logger.debug(f"There is only one 'id' for this component type - resetting the "
                         f"default electrumx id={component_id}")
            self.reset_electrumx()

        elif component_data.get('component_type') == ComponentName.ELECTRUMSV:
            self.reset_electrumsv_wallet(component_id)

        elif component_data.get('component_type') == ComponentName.INDEXER:
            logger.debug(f"The Indexer component type is not supported at this time.")

        elif component_data.get('component_type') == ComponentName.STATUS_MONITOR:
            logger.error("resetting the status monitor is not supported at this time...")

    def reset_component_by_type(self):
        if ComponentName.NODE in self.app_state.reset_set or len(self.app_state.reset_set) == 0:
            self.reset_node()

        if ComponentName.ELECTRUMX in self.app_state.reset_set or len(
                self.app_state.reset_set) == 0:
            self.reset_electrumx()

        if ComponentName.INDEXER in self.app_state.reset_set or len(
                self.app_state.reset_set) == 0:
            logger.error("resetting indexer is not supported at this time...")

        if ComponentName.STATUS_MONITOR in self.app_state.reset_set \
                or len(self.app_state.reset_set) == 0:
            logger.error("resetting the status monitor is not supported at this time...")

        if ComponentName.ELECTRUMSV in self.app_state.reset_set or len(
                self.app_state.reset_set) == 0:
            self.reset_electrumsv_wallet()
            self.app_state.stop_set.add(ComponentName.ELECTRUMSV)
