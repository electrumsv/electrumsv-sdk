import json
import logging
import os
import shlex
import subprocess
import sys
import threading
from pathlib import Path
from typing import List, Dict

import tailer
from electrumsv_node import electrumsv_node

logger = logging.getLogger("utils")
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


def checkout_branch(branch: str):
    if branch != "":
        subprocess.run(f"git checkout {branch}", shell=True, check=True)


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
        subprocess.run(f"kill -9 {pid}", shell=True)
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


def get_sdk_datadir():
    sdk_home_datadir = None
    if sys.platform == "win32":
        sdk_home_datadir = Path(os.environ.get("LOCALAPPDATA")) / "ElectrumSV-SDK"
    if sdk_home_datadir is None:
        sdk_home_datadir = Path.home() / ".electrumsv-sdk"
    return sdk_home_datadir


def tail(logfile, stop_event: threading.Event):
    for line in tailer.follow(open(logfile), delay=0.3):
        if stop_event.is_set():
            break
        print(line)


def spawn_inline(command: str, env_vars: Dict=None, logfile: Path=None):
    """only for running servers with logging requirements - not for simple commands"""

    if not env_vars:
        env_vars = {}

    stop_event = threading.Event()
    try:
        if logfile:
            with open(f'{logfile}', 'w') as logfile_handle:
                # direct logs to file
                if sys.platform == 'win32':
                    process = subprocess.Popen(command, stdout=logfile_handle,
                        stderr=logfile_handle, env=os.environ.update(env_vars))
                elif sys.platform in {'linux', 'windows'}:
                    process = subprocess.Popen(f"{command}", shell=True, stdout=logfile_handle,
                        stderr=logfile_handle, env=os.environ.update(env_vars))

                # tail logs from file into stdout (blocks in a thread)
                t = threading.Thread(target=tail, args=(logfile, stop_event), daemon=True)
                t.start()

                process.wait()
                stop_event.set()  # trigger thread to stop tailing log file

                if process.returncode != 0:
                    logger.error(f"process crashed: see {logfile} for full logs")
                    for line in tailer.tail(open(logfile), lines=15):
                        print(line)
        else:
            if sys.platform == 'win32':
                process = subprocess.Popen(command, env=os.environ.update(env_vars))
                process.wait()
            elif sys.platform in {'linux', 'windows'}:
                process = subprocess.Popen(f"{command}", shell=True,
                    env=os.environ.update(env_vars))
                process.wait()
    except KeyboardInterrupt:
        stop_event.set()
        sys.exit(1)


def spawn_background(command: str, env_vars: Dict, logfile: Path=None) -> subprocess.Popen:
    if logfile:
        with open(f'{logfile}', 'w') as logfile_handle:
            # direct stdout and stderr to file
            if sys.platform == "win32":
                process = subprocess.Popen(command, stdout=logfile_handle, stderr=logfile_handle,
                    env=os.environ.update(env_vars), creationflags=subprocess.DETACHED_PROCESS)
            else:
                process = subprocess.Popen(f"nohup {command} &", shell=True, stdout=logfile_handle,
                    stderr=logfile_handle, env=os.environ.update(env_vars))
    else:
        # no logging
        if sys.platform == "win32":
            process = subprocess.Popen(command, env=os.environ.update(env_vars),
                creationflags=subprocess.DETACHED_PROCESS)
        else:
            process = subprocess.Popen(f"nohup {command} &", shell=True,
                env=os.environ.update(env_vars))
    return process


def wrap_with_single_quote(string: str):
    return "'" + string + "'"


def spawn_new_terminal(command: str, env_vars: Dict, logfile: Path=None) -> subprocess.Popen:
    run_inline_script = Path(MODULE_DIR).joinpath("scripts/run_inline.py")
    command = f"{sys.executable} {run_inline_script} " \
              f"--command {wrap_with_single_quote(command)}"

    command += f" --env_vars {wrap_with_single_quote(json.dumps(env_vars))}" \

    if logfile:
        command += f" --logfile {wrap_with_single_quote(str(logfile))}"

    if sys.platform in ('linux', 'darwin'):
        split_command = shlex.split(f"xterm -fa 'Monospace' -fs 10 -e {command}", posix=1)
        process = subprocess.Popen(split_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)

    elif sys.platform == 'win32':
        split_command = shlex.split(f"cmd /c {command}", posix=0)
        process = subprocess.Popen(
            split_command, creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    return process
