import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path

import psutil
from electrumsv_node import electrumsv_node

from .components import ComponentName

logger = logging.getLogger("utils")
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

def checkout_branch(branch: str):
    if branch != "":
        subprocess.run(f"git checkout {branch}", shell=True, check=True)


def make_bat_file(filename, commandline_string=None, env_vars=None, separate_lines=None):
    if not env_vars:
        env_vars = {}

    open(filename, "w").close()
    with open(filename, "a") as f:
        f.write("@echo off\n")
        for key, val in env_vars.items():
            f.write(f"set {key}={val}\n")

        if separate_lines:
            for line in separate_lines:
                f.write(line)

        if commandline_string:
            commandline_string_split = shlex.split(commandline_string, posix=0)
            for subcmd in commandline_string_split:
                f.write(f"{subcmd}" + " ")
        f.write("\n")
        f.write("pause\n")


def make_bash_file(filename, commandline_string=None, env_vars=None, separate_lines=None):
    if not env_vars:
        env_vars = {}

    open(filename, "w").close()
    with open(filename, "a") as f:
        f.write("#!/bin/bash\n")
        f.write("set echo off\n")
        for key, val in env_vars.items():
            f.write(f"export {key}={val}\n")

        if separate_lines:
            for line in separate_lines:
                f.write(line)

        if commandline_string:
            commandline_string_split = shlex.split(commandline_string, posix=0)
            for subcmd in commandline_string_split:
                f.write(f"{subcmd}" + " ")
        f.write("\n")
        f.write("exit")
    os.system(f'chmod 777 {filename}')


def make_shell_script_for_component(component_name, commandline_string=None, env_vars=None,
        multiple_lines=None):
    if sys.platform == "win32":
        make_bat_file(component_name + ".bat", commandline_string, env_vars, multiple_lines)

    elif sys.platform in ["linux", "darwin"]:
        make_bash_file(component_name + ".sh", commandline_string, env_vars, multiple_lines)


def add_esv_default_args(commandline_string, esv_data_dir, port):
    commandline_string += (
        f" --portable --dir {esv_data_dir} "
        f"--regtest daemon -dapp restapi --v=debug --file-logging "
        f"--restapi --restapi-port={port} --server=127.0.0.1:51001:t "
    )
    return commandline_string


def make_esv_custom_script(base_cmd, env_vars, component_args, esv_data_dir):
    """if cli args are supplied to electrumsv then it gives a "clean slate" (discarding the default
    configuration. (but ensures that the --dir and --restapi flags are set if not already)"""
    commandline_string = base_cmd
    additional_args = " ".join(component_args)
    commandline_string += " " + additional_args
    if "--dir" not in component_args:
        commandline_string += " " + f"--dir {esv_data_dir}"

    # so that polling works
    if "--restapi" not in component_args:
        commandline_string += " " + f"--restapi"

    make_shell_script_for_component(ComponentName.ELECTRUMSV, commandline_string, env_vars)


def make_esv_daemon_script(base_cmd, env_vars, esv_data_dir, port):
    commandline_string = base_cmd + (
        f" --portable --dir {esv_data_dir} "
        f"--regtest daemon -dapp restapi --v=debug --file-logging "
        f"--restapi --restapi-port={port} --server=127.0.0.1:51001:t --restapi-user rpcuser"
        f" --restapi-password= "
    )
    make_shell_script_for_component(ComponentName.ELECTRUMSV, commandline_string, env_vars)


def make_esv_gui_script(base_cmd, env_vars, esv_data_dir, port):
    commandline_string = base_cmd + (
        f" gui --regtest --restapi --restapi-port={port} "
        f"--v=debug --file-logging --server=127.0.0.1:51001:t --dir {esv_data_dir}"
    )
    make_shell_script_for_component(ComponentName.ELECTRUMSV, commandline_string, env_vars)


def topup_wallet():
    logger.debug("Topping up wallet...")
    nblocks = 1
    toaddress = "mwv1WZTsrtKf3S9mRQABEeMaNefLbQbKpg"
    result = electrumsv_node.call_any("generatetoaddress", nblocks, toaddress)
    if result.status_code == 200:
        logger.debug(f"Generated {nblocks}: {result.json()['result']} to {toaddress}")


def cast_str_int_args_to_int(node_args):
    int_indices = []
    for index, arg in enumerate(node_args):
        if arg.isdigit():
            int_indices.append(index)

    for i in int_indices:
        node_args[i] = int(node_args[i])
    return node_args


def trace_processes_for_cmd(command):
    processes = []
    for p in psutil.process_iter():
        try:
            process_name = p.name()
            if command.stem in process_name:
                processes.append(p.pid)
        except Exception:
            pass
    return processes


def trace_pid(command):
    """
    Linux workaround:
    - gnome-terminal only ever returns back an ephemeral pid and makes it basically impossible
    to retrieve the pid of spawned tasks inside of the new window.

    Workaround adapted from:
    'https://stackoverflow.com/questions/55880659/
    get-process-id-of-command-executed-inside-terminal-in-python-subprocess'
    """
    processes = trace_processes_for_cmd(command)
    processes.sort()
    # take highest pid number (most recently allocated) if there are multiple instances
    process_handle = psutil.Process(processes[-1])
    return process_handle


def is_remote_repo(repo: str):
    return repo == "" or repo.startswith("https://")


def read_sdk_version():
    with open(Path(MODULE_DIR).joinpath('__init__.py'), 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                version = line.strip().split('= ')[1].strip("'")
                break
    return version
