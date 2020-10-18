import logging
import os
import subprocess
import time
from pathlib import Path

from electrumsv_sdk.components import ComponentOptions
from electrumsv_sdk.utils import get_directory_name

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def normalize_wallet_name(wallet_name: str):
    if wallet_name is not None:
        if not wallet_name.endswith(".sqlite"):
            wallet_name += ".sqlite"
    else:
        wallet_name = "worker1.sqlite"
    return wallet_name


def create_wallet(app_state, wallet_name: str = None):
    try:
        logger.debug("Creating wallet...")
        wallet_name = normalize_wallet_name(wallet_name)
        wallet_path = app_state.component_datadir.joinpath(f"regtest/wallets/{wallet_name}")
        password = "test"

        command = (
            f"electrumsv-sdk start --background --repo"
            f"={app_state.global_cli_flags[ComponentOptions.REPO]} "
            f"electrumsv create_wallet --wallet {wallet_path} "
            f"--walletpassword {password} --portable --no-password-check")

        subprocess.run(command, shell=True, check=True)
        logger.debug(f"New wallet created at : {wallet_path} ")
    except Exception as e:
        logger.exception("unexpected problem creating new wallet")
        raise


def delete_wallet(app_state, wallet_name: str = None):
    wallet_name = normalize_wallet_name(wallet_name)
    esv_wallet_db_directory = app_state.component_datadir.joinpath("regtest/wallets")
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


def cleanup(app_state):
    id = app_state.global_cli_flags[ComponentOptions.ID]
    if id:
        app_state.run_command_current_shell(f"electrumsv-sdk stop --id={id}")
    else:
        app_state.run_command_current_shell(f"electrumsv-sdk stop electrumsv")
