import logging
import os
import subprocess
import time
from pathlib import Path

from .install import configure_paths
from electrumsv_sdk.components import ComponentOptions
from electrumsv_sdk.utils import get_directory_name, split_command

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def normalize_wallet_name(wallet_name: str):
    if wallet_name is not None:
        if not wallet_name.endswith(".sqlite"):
            wallet_name += ".sqlite"
    else:
        wallet_name = "worker1.sqlite"
    return wallet_name


def feed_commands_to_esv(app_state, command_string):
    esv_launcher = str(app_state.component_source_dir.joinpath("electrum-sv"))
    esv_datadir = app_state.component_datadir
    component_args = split_command(command_string)
    if component_args:
        additional_args = " ".join(component_args)
        line = f"{app_state.python} {esv_launcher} {additional_args}"
        if "--dir" not in component_args:
            line += " " + f"--dir {esv_datadir}"
    return line


def create_wallet(app_state, datadir: Path, wallet_name: str = None):
    repo = app_state.global_cli_flags[ComponentOptions.REPO]
    branch = app_state.global_cli_flags[ComponentOptions.BRANCH]
    try:
        configure_paths(app_state, repo, branch)
        logger.debug("Creating wallet...")
        wallet_name = normalize_wallet_name(wallet_name)
        wallet_path = datadir.joinpath(f"regtest/wallets/{wallet_name}")
        password = "test"

        # New wallet
        command_string = f"create_wallet --wallet {wallet_path} --walletpassword" \
                         f" {password} --portable --no-password-check"
        line = feed_commands_to_esv(app_state, command_string)
        process = subprocess.Popen(line, shell=True)
        process.wait()
        logger.debug(f"New wallet created at : {wallet_path} ")

        # New account
        command_string = (
            f"create_account --wallet {wallet_path} --walletpassword {password} --portable "
            f"--no-password-check")
        line = feed_commands_to_esv(app_state, command_string)
        process = subprocess.Popen(line, shell=True)
        process.wait()
        logger.debug(f"New standard (bip32) account created for: '{wallet_path}'")

    except Exception as e:
        logger.exception("unexpected problem creating new wallet")
        raise


def delete_wallet(datadir: Path, wallet_name: str = None):
    esv_wallet_db_directory = datadir.joinpath("regtest/wallets")
    os.makedirs(esv_wallet_db_directory, exist_ok=True)

    try:
        time.sleep(1)
        logger.debug("Deleting wallet...")
        logger.debug(
            "Wallet directory before: %s", os.listdir(esv_wallet_db_directory),
        )
        file_names = os.listdir(esv_wallet_db_directory)
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

