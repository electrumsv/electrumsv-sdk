import json
import logging
import os
import shlex
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import List, Dict, Optional

import colorama
import psutil
import tailer
from electrumsv_node import electrumsv_node
from .components import Component, ComponentStore
from .constants import ComponentState, SUCCESS_EXITCODE, SIGINT_EXITCODE, SIGKILL_EXITCODE

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


def get_parent_and_child_pids(parent_pid):
    try:
        pids = []
        parent = psutil.Process(parent_pid)
        pids.append(parent.pid)
        for child in parent.children(recursive=True):
            pids.append(child.pid)
        return pids
    except psutil.NoSuchProcess:
        pass


def sigint(pid):
    """attempt graceful shutdown via sigint"""
    if sys.platform in ("linux", "darwin"):
        try:
            os.kill(pid, signal.SIGINT)
        except (SystemError, OSError):
            pass

    elif sys.platform == "win32":
        try:
            os.kill(pid, signal.CTRL_C_EVENT)
        except (SystemError, OSError):
            pass


def sigkill(parent_pid):
    """kill process if sigint failed"""
    pids = get_parent_and_child_pids(parent_pid)
    if pids:
        for pid in pids:
            if sys.platform in ('linux', 'darwin'):
                process = subprocess.Popen(f"/bin/bash -c 'kill -9 {pid}'", shell=True)
                process.wait()
            elif sys.platform == 'win32':
                if psutil.pid_exists(pid):
                    subprocess.run(f"taskkill.exe /PID {pid} /T /F")


def kill_by_pid(pid: id):
    """kills parent and all children"""
    # todo - it may make sense to add an optional timeout for waiting on a graceful shutdown
    #  via sigint before escalating to sigkill/sigterm - this would be specified for each plugin
    pids = get_parent_and_child_pids(parent_pid=pid)
    if pids:
        for pid in pids:
            sigint(pid)

        if psutil.pid_exists(pid):
            sigkill(parent_pid=pid)


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


def tail(logfile):
    colorama.init()
    for line in tailer.follow(open(logfile), delay=0.3):
        # "https://www.devdungeon.com/content/colorize-terminal-output-python"
        # If using Windows, init() will cause anything sent to stdout or stderr
        # will have ANSI color codes converted to the Windows versions. Hooray!
        # If you are already using an ANSI compliant shell, it won't do anything
        print(line)


def update_status_monitor(pid: int, component_state: str, id: str=None, component_name: str=None,
        src: Path=None, logfile: Path=None, status_endpoint: str=None, metadata: Dict=None) -> None:

    component_info = Component(id, pid, component_name, str(src),
        status_endpoint=status_endpoint, component_state=component_state,
        metadata=metadata, logging_path=logfile)

    # can re-instantiate ComponentStore in the child process (it is multiprocess safe)
    component_store = ComponentStore()
    component_store.update_status_file(component_info)


def spawn_inline(command: str, env_vars: Dict=None, id: str=None, component_name:
        str=None, src: Path=None, logfile: Path=None, status_endpoint: str=None,
            metadata: Dict=None) -> None:
    """only for running servers with logging requirements - not for simple commands"""
    def update_state(process, component_state: str):
        update_status_monitor(pid=process.pid, component_state=component_state, id=id,
            component_name=component_name, src=src, logfile=logfile,
            status_endpoint=status_endpoint, metadata=metadata)

    def on_start(process):
        update_state(process, ComponentState.RUNNING)

    def on_exit(process):
        # on windows signal.CTRL_C_EVENT gives back SUCCESS_EXITCODE (0)
        if process.returncode in {SUCCESS_EXITCODE, SIGINT_EXITCODE, SIGKILL_EXITCODE}:
            update_state(process, ComponentState.STOPPED)
        elif process.returncode != SUCCESS_EXITCODE:
            update_state(process, ComponentState.FAILED)

    env = os.environ.copy()
    if not env_vars:
        env_vars = {}
    env.update(env_vars)

    t: Optional[threading.Thread] = None
    try:
        if logfile:
            with open(f'{logfile}', 'w') as logfile_handle:
                # direct logs to file
                if sys.platform == 'win32':
                    process = subprocess.Popen(command, stdout=logfile_handle,
                        stderr=logfile_handle, env=env)
                elif sys.platform in {'linux', 'darwin'}:
                    process = subprocess.Popen(f"{command}", shell=True, stdout=logfile_handle,
                        stderr=logfile_handle, env=env)

                # tail logs from file into stdout (blocks in a thread)
                t = threading.Thread(target=tail, args=(logfile, ), daemon=True)
                t.start()

                on_start(process)
                process.wait()
                on_exit(process)

                t.join(0.5)  # allow time for background thread to dump logs
        else:
            if sys.platform == 'win32':
                process = subprocess.Popen(command, env=env)
            elif sys.platform in {'linux', 'darwin'}:
                process = subprocess.Popen(f"{command}", shell=True, env=env)

            on_start(process)
            process.wait()
            on_exit(process)

    except KeyboardInterrupt:
        if t:
            t.join(0.5)
        sys.exit(1)


def spawn_background_supervised(command: str, env_vars: Dict, id: str=None, component_name:
        str=None, src: Path=None, logfile: Path=None, status_endpoint: str=None,
            metadata: Dict=None) -> None:
    """spawns a child process that can wait for the process to exit and check the returncode"""
    run_background_script = Path(MODULE_DIR).joinpath("scripts/run_background.py")
    component_info = Component(id, None, component_name, str(src),
        status_endpoint=status_endpoint, component_state=None,
        metadata=metadata, logging_path=logfile)
    component_json = json.dumps(component_info.to_dict())
    os.environ["SCRIPT_COMPONENT_INFO"] = wrap_and_escape_text(component_json)
    os.environ["SCRIPT_COMMAND"] = wrap_and_escape_text(command)

    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    if sys.platform == "win32":
        cmd = shlex.split(f"{sys.executable} {run_background_script}", posix=False)
        subprocess.Popen(cmd, env=env, creationflags=subprocess.DETACHED_PROCESS)
    else:
        cmd = shlex.split(f"{sys.executable} {run_background_script}", posix=True)
        subprocess.Popen(cmd, env=env)


def spawn_background(command: str, env_vars: Dict, id: str=None, component_name:
        str=None, src: Path=None, logfile: Path=None, status_endpoint: str=None,
            metadata: Dict=None) -> None:

    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    def update_state(process, component_state: str):
        update_status_monitor(pid=process.pid, component_state=component_state, id=id,
            component_name=component_name, src=src, logfile=logfile,
            status_endpoint=status_endpoint, metadata=metadata)

    def on_start(process):
        update_state(process, ComponentState.RUNNING)

    def on_exit(process):
        # on windows signal.CTRL_C_EVENT gives back SUCCESS_EXITCODE (0)
        if process.returncode in {SUCCESS_EXITCODE, SIGINT_EXITCODE, SIGKILL_EXITCODE}:
            update_state(process, ComponentState.STOPPED)
        elif process.returncode != SUCCESS_EXITCODE:
            update_state(process, ComponentState.FAILED)

    if logfile:
        with open(f'{logfile}', 'w') as logfile_handle:
            # direct stdout and stderr to file
            if sys.platform == "win32":
                process = subprocess.Popen(command, stdout=logfile_handle, stderr=logfile_handle,
                    env=env, creationflags=subprocess.DETACHED_PROCESS)
            else:
                process = subprocess.Popen(shlex.split(command, posix=1), stdout=logfile_handle,
                    stderr=logfile_handle, env=env)
    else:
        # no logging
        if sys.platform == "win32":
            process = subprocess.Popen(command, env=env,
                creationflags=subprocess.DETACHED_PROCESS)
        else:
            process = subprocess.Popen(shlex.split(command), env=env)

    on_start(process)
    process.wait()
    on_exit(process)


def wrap_and_escape_text(string: str):
    assert isinstance(string, str), "string type required"
    return "\'" + string.replace('"', '\\"') + "\'"


def spawn_new_terminal(command: str, env_vars: Dict, id: str=None, component_name:
        str=None, src: Path=None, logfile: Path=None, status_endpoint: str=None,
            metadata: Dict=None) -> None:

    component_info = Component(id=id, pid=None, component_type=component_name, location=str(src),
        status_endpoint=status_endpoint, component_state=None, metadata=metadata,
        logging_path=logfile)
    component_json = json.dumps(component_info.to_dict())

    run_inline_script = Path(MODULE_DIR).joinpath("scripts/run_inline.py")
    command = f"{sys.executable} {run_inline_script} " \
              f"--command {wrap_and_escape_text(command)}"

    command += f" --env_vars {wrap_and_escape_text(json.dumps(env_vars))}"
    command += f" --component_info {wrap_and_escape_text(component_json)}"

    if sys.platform in 'linux':
        split_command = shlex.split(f"xterm -fa 'Monospace' -fs 10 -e {command}", posix=1)
        subprocess.Popen(split_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)

    elif sys.platform == 'darwin':
        split_command = ['osascript', '-e',
            f"tell application \"Terminal\" to do script \"{command}\""]
        subprocess.Popen(split_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)

    elif sys.platform == 'win32':
        split_command = shlex.split(f"cmd /c {command}", posix=0)
        subprocess.Popen(split_command, creationflags=subprocess.CREATE_NEW_CONSOLE)
