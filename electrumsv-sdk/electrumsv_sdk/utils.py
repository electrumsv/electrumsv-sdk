import datetime
import json
import logging
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests
from electrumsv_node import electrumsv_node

logger = logging.getLogger("utils")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def checkout_branch(branch: str):
    if branch != "":
        subprocess.run(f"git checkout {branch}", shell=True, check=True)


def make_bat_file(filename, commandline_string_split, env_vars):
    open(filename, "w").close()
    with open(filename, "a") as f:
        f.write("@echo off\n")
        for key, val in env_vars.items():
            f.write(f"set {key}={val}\n")
        for subcmd in commandline_string_split:
            f.write(f"{subcmd}" + " ")
        f.write("\n")
        f.write("pause\n")


def make_bash_file(filename, commandline_string_split, env_vars):
    open(filename, "w").close()
    with open(filename, "a") as f:
        f.write("#!/bin/bash\n")
        f.write("set echo off\n")
        for key, val in env_vars.items():
            f.write(f"export {key}={val}\n")
        for subcmd in commandline_string_split:
            f.write(f"{subcmd}" + " ")
        f.write("\n")
        f.write("exit")


def add_esv_custom_args(commandline_string, component_args, esv_data_dir):
    additional_args = " ".join(component_args)
    commandline_string += " " + additional_args
    if "--dir" not in component_args:
        commandline_string += " " + f"--dir {esv_data_dir}"

    # so that polling works
    if "--restapi" not in component_args:
        commandline_string += " " + f"--restapi"
    return commandline_string


def make_esv_daemon_script(esv_script, electrumsv_env_vars, esv_data_dir, port,
        component_args=None):
    if component_args is not None:
        commandline_string = (
            f"{sys.executable} {esv_script}"
        )
        commandline_string = add_esv_custom_args(commandline_string, component_args, esv_data_dir)
    else:
        commandline_string = (
            f"{sys.executable} {esv_script} --regtest daemon -dapp restapi "
            f"--v=debug --file-logging --restapi --restapi-port={port} --server=127.0.0.1:51001:t "
            f"--dir {esv_data_dir}"
        )

    if sys.platform == "win32":
        commandline_string_split = shlex.split(commandline_string, posix=0)
        make_bat_file("electrumsv.bat", commandline_string_split, electrumsv_env_vars)

    elif sys.platform in ["linux", "darwin"]:
        commandline_string_split = shlex.split(commandline_string, posix=1)
        filename = "electrumsv.sh"
        make_bash_file(filename, commandline_string_split, electrumsv_env_vars)
        os.system(f'chmod 777 {filename}')


def make_esv_gui_script(esv_script, electrumsv_env_vars, esv_data_dir, port,
        component_args=None):
    if component_args is not None:
        commandline_string = (
            f"{sys.executable} {esv_script}"
        )
        commandline_string = add_esv_custom_args(commandline_string, component_args, esv_data_dir)
    else:
        commandline_string = (
            f"{sys.executable} {esv_script} gui --regtest --restapi --restapi-port={port} "
            f"--v=debug --file-logging --server=127.0.0.1:51001:t --dir {esv_data_dir}"
        )

    if sys.platform == "win32":
        commandline_string_split = shlex.split(commandline_string, posix=0)
        make_bat_file("electrumsv-gui.bat", commandline_string_split, electrumsv_env_vars)

    elif sys.platform in ["linux", "darwin"]:
        commandline_string_split = shlex.split(commandline_string, posix=1)
        filename = "electrumsv-gui.sh"
        make_bash_file("electrumsv-gui.sh", commandline_string_split, electrumsv_env_vars)
        os.system(f'chmod 777 {filename}')


def get_str_datetime():
    return datetime.datetime.now().strftime(TIME_FORMAT)


def topup_wallet():
    logger.debug("topping up wallet...")
    nblocks = 1
    toaddress = "mwv1WZTsrtKf3S9mRQABEeMaNefLbQbKpg"
    result = electrumsv_node.call_any("generatetoaddress", nblocks, toaddress)
    if result.status_code == 200:
        logger.debug(f"generated {nblocks}: {result.json()['result']} to {toaddress}")


def create_wallet():
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
        logger.debug(f"new wallet created in {response.json()['value']['new_wallet']}")
    except Exception as e:
        logger.exception(e)


def delete_wallet(app_state):
    esv_wallet_db_directory = app_state.electrumsv_regtest_wallets_dir
    os.makedirs(esv_wallet_db_directory, exist_ok=True)

    try:
        time.sleep(1)
        logger.debug("deleting wallet...")
        logger.debug(
            "wallet directory before: %s", os.listdir(esv_wallet_db_directory),
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
            "wallet directory after: %s", os.listdir(esv_wallet_db_directory),
        )
    except Exception as e:
        logger.exception(e)
    else:
        return


def cast_str_int_args_to_int(node_args):
    int_indices = []
    for index, arg in enumerate(node_args):
        if arg.isdigit():
            int_indices.append(index)

    for i in int_indices:
        node_args[i] = int(node_args[i])
    return node_args


def trace_pid(command):
    """
    Linux workaround:
    - gnome-terminal only ever returns back an ephemeral pid and makes it basically impossible to retrieve
    the pid of spawned tasks inside of the new window.

    Workaround adapted from:
    'https://stackoverflow.com/questions/55880659/
    get-process-id-of-command-executed-inside-terminal-in-python-subprocess'
    """
    processes = []
    for p in psutil.process_iter():
        try:
            process_name = p.name()
            if command.stem in process_name:
                processes.append(p.pid)
        except Exception:
            pass
    processes.sort()
    # take highest pid number (most recently allocated) if there are multiple instances
    process_handle = psutil.Process(processes[-1])
    return process_handle
