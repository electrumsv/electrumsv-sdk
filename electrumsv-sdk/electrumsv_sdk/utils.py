import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Dict

import psutil
from electrumsv_node import electrumsv_node

logger = logging.getLogger("utils")
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


def checkout_branch(branch: str):
    if branch != "":
        subprocess.run(f"git checkout {branch}", shell=True, check=True)


def make_bat_file(filename: str, list_of_shell_commands: List[str]):
    """wraps a list of shell commands with @echo off and 'pause' and outputs it to a
    <component_name>.bat file"""
    open(filename, "w").close()
    with open(filename, "a") as f:
        f.write("@echo off\n")
        if list_of_shell_commands:
            for line in list_of_shell_commands:
                split_command = shlex.split(line, posix=0)
                f.write(" ".join(split_command))
                f.write('\n')
        f.write("pause\n")


def make_bash_file(filename: str, list_of_shell_commands: List[str]):
    """wraps a list of shell commands with 'set echo off' and 'exit' and outputs it to a
    <component_name>.bat file"""
    open(filename, "w").close()
    with open(filename, "a") as f:
        f.write("#!/bin/bash\n")
        f.write("set echo off\n")
        if list_of_shell_commands:
            for line in list_of_shell_commands:
                split_command = shlex.split(line, posix=1)
                f.write(" ".join(split_command))
                f.write("\n")
        f.write("exit")
    os.system(f'chmod 777 {filename}')


def topup_wallet():
    logger.debug("Topping up wallet...")
    nblocks = 1
    toaddress = "mwv1WZTsrtKf3S9mRQABEeMaNefLbQbKpg"
    result = electrumsv_node.call_any("generatetoaddress", nblocks, toaddress)
    if result.status_code == 200:
        logger.debug(f"Generated {nblocks}: {result.json()['result']} to {toaddress}")


def cast_str_int_args_to_int(node_args: List[str]) -> List[str]:
    int_indices = []
    for index, arg in enumerate(node_args):
        if arg.isdigit():
            int_indices.append(index)

    for i in int_indices:
        node_args[i] = int(node_args[i])
    return node_args


def trace_processes_for_cmd(command: str) -> List[int]:
    str(command)
    processes = []
    for p in psutil.process_iter():
        try:
            cmd = p.cmdline()
            for subcommand in command.split(" "):
                if subcommand in cmd:
                    processes.append(p.pid)
        except Exception:
            pass
    return processes


def trace_pid(command: str) -> psutil.Process:
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


def port_is_in_use(port) -> bool:
    netstat_cmd = "netstat -an"
    if sys.platform in {'linux', 'darwin'}:
        netstat_cmd = "netstat -antu"

    filter_set = {f'127.0.0.1:{port}', f'0.0.0.0:{port}', f'[::]:{port}', f'[::1]:{port}'}
    result = subprocess.run(netstat_cmd, shell=True, check=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in str(result.stdout).split(r'\r\n'):
        columns = line.split()
        if len(columns) > 1 and columns[1] in filter_set:
            return True
    return False


def get_directory_name(component__file__):
    MODULE_DIR = os.path.dirname(os.path.abspath(component__file__))
    component_name = os.path.basename(MODULE_DIR)
    return component_name


def kill_by_pid(pid: id):
    if sys.platform in ("linux", "darwin"):
        subprocess.run(f"pkill -P {pid}", shell=True)
    elif sys.platform == "win32":
        subprocess.run(f"taskkill.exe /PID {pid} /T /F")


def kill_process(component_dict: Dict):
    pid = component_dict.get('pid')
    kill_by_pid(pid)


def is_default_component_id(component_name, component_id):
    return component_name + str(1) == component_id


def split_command(command: str) -> List[str]:
    if sys.platform == 'win32':
        split_command = shlex.split(command, posix=0)
    elif sys.platform in {'darwin', 'linux'}:
        split_command = shlex.split(command, posix=1)
    else:
        raise NotImplementedError("OS not supported")
    return split_command

def is_docker():
    path = '/proc/self/cgroup'
    return (
        os.path.exists('/.dockerenv') or
        os.path.isfile(path) and any('docker' in line for line in open(path))
    )
