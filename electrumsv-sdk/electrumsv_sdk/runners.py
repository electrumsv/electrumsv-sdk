import asyncio
import json
import logging
import subprocess
import sys
import time

import aiorpcx
import requests
from electrumsv_node import electrumsv_node
from electrumsv_sdk.component_state import Component, ComponentType, ComponentName, ComponentState
from electrumsv_sdk.reset import reset_node, reset_electrumx, reset_electrumsv_wallet

from .app_state import AppState

logger = logging.getLogger("runners")


async def is_electrumx_running():
    for sleep_time in (1, 2, 3):
        try:
            logger.debug("polling electrumx...")
            async with aiorpcx.connect_rs(host="127.0.0.1", port=51001) as session:
                result = await session.send_request("server.version")
                if result[1] == "1.4":
                    logger.debug("electrumx online")
                    return True
        except Exception as e:
            pass

        await asyncio.sleep(sleep_time)
    return False


def is_electrumsv_running():
    for sleep_time in (3, 3, 3):
        try:
            logger.debug("polling electrumsv...")
            result = requests.get("http://127.0.0.1:9999/")
            result.raise_for_status()
            assert result.json()['status'] == 'success'
            logger.debug("electrumsv online")
            return True
        except Exception as e:
            pass

        time.sleep(sleep_time)
    return False


def run_electrumsv_node():
    process = electrumsv_node.start()
    time.sleep(0.1)
    process.poll()

    component = Component(
        pid=process.pid,
        process_name=ComponentName.NODE,
        process_type=ComponentType.NODE,
        endpoint="http://127.0.0.1:18332",
        component_state=ComponentState.NONE,
        location=None,
        metadata={},
        logging_path=None,
    )
    if process.returncode != 0:
        component.component_state = ComponentState.Failed
    else:
        component.component_state = ComponentState.Running
    AppState.update_status(component)

    # process handle not returned because node is stopped via rpc


def run_electrumx_server():
    logger.debug(f"starting RegTest electrumx server...")
    if sys.platform == "win32":
        electrumx_server_script = AppState.run_scripts_dir.joinpath("electrumx.bat")
    else:
        electrumx_server_script = AppState.run_scripts_dir.joinpath("electrumx.sh")

    process = subprocess.Popen(
        f"{electrumx_server_script}", creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    component = Component(
        pid=process.pid,
        process_name=ComponentName.ELECTRUMX,
        process_type=ComponentType.ELECTRUMX,
        endpoint="http://127.0.0.1:51001",
        component_state=ComponentState.NONE,
        location=AppState.electrumx_dir.__str__(),
        metadata={"data_dir": AppState.electrumx_data_dir.__str__()},
        logging_path=None,
    )

    is_running = asyncio.run(is_electrumx_running())
    if not is_running:
        component.component_state = ComponentState.Failed
    else:
        component.component_state = ComponentState.Running
    AppState.update_status(component)
    return process


def disable_rest_api_authentication():
    path_to_config = AppState.electrumsv_regtest_config_dir.__str__()

    with open(path_to_config, "r") as f:
        config = json.load(f)
        config["rpcpassword"] = ""
        config["rpcuser"] = "user"

    with open(path_to_config, "w") as f:
        f.write(json.dumps(config, indent=4))


def start_and_stop_ESV(electrumsv_server_script):
    # Ugly hack (first time run through need to start then stop ESV wallet to make config files)
    logger.debug(
        "starting RegTest electrumsv daemon for the first time - initializing wallet - "
        "standby..."
    )
    process = subprocess.Popen(
        f"{electrumsv_server_script}", creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    time.sleep(7)
    subprocess.run(f"taskkill.exe /PID {process.pid} /T /F")


def run_electrumsv_daemon(is_first_run=False):
    """Todo - this currently uses ugly hacks with starting and stopping the ESV wallet in order to:
    1) generate the config files (so that it can be directly edited) - would be obviated by
    fixing this: https://github.com/electrumsv/electrumsv/issues/111
    2) newly created wallet doesn't seem to be fully useable until after stopping the daemon."""
    if sys.platform == "win32":
        electrumsv_server_script = AppState.run_scripts_dir.joinpath("electrumsv.bat")
    else:
        electrumsv_server_script = AppState.run_scripts_dir.joinpath("electrumsv.sh")

    try:
        disable_rest_api_authentication()
    except FileNotFoundError:  # is_first_run = True
        start_and_stop_ESV(electrumsv_server_script)  # generates config json file
        disable_rest_api_authentication()  # now this will work
        return run_electrumsv_daemon(is_first_run=True)

    logger.debug(f"starting RegTest electrumsv daemon...")
    process = subprocess.Popen(
        f"{electrumsv_server_script}", creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    if is_first_run:
        time.sleep(7)
        reset_electrumsv_wallet()  # create first-time wallet
        time.sleep(1)
        subprocess.run(f"taskkill.exe /PID {process.pid} /T /F", check=True)
        return run_electrumsv_daemon(is_first_run=False)

    component = Component(
        pid=process.pid,
        process_name=ComponentName.ELECTRUMSV,
        process_type=ComponentType.ELECTRUMSV,
        endpoint="http://127.0.0.1:9999",
        component_state=ComponentState.NONE,
        location=AppState.electrumsv_regtest_dir.__str__(),
        metadata={"config": AppState.electrumsv_regtest_config_dir.__str__()},
        logging_path=AppState.electrumsv_data_dir.joinpath("logs").__str__(),
    )

    is_running = is_electrumsv_running()
    if not is_running:
        component.component_state = ComponentState.Failed
    else:
        component.component_state = ComponentState.Running
    AppState.update_status(component)
    return process



def startup():
    print()
    print()
    print("running stack...")

    procs = []
    if AppState.NODE in AppState.required_dependencies_set:
        run_electrumsv_node()
        time.sleep(2)

    if AppState.ELECTRUMX in AppState.required_dependencies_set:
        electrumx_process = run_electrumx_server()
        procs.append(electrumx_process.pid)

    if AppState.ELECTRUMSV in AppState.required_dependencies_set:
        esv_process = run_electrumsv_daemon()
        procs.append(esv_process.pid)

    return procs


def start():
    procs = startup()
    with open(AppState.proc_ids_path, "w") as f:
        f.write(json.dumps(procs))
    AppState.save_repo_paths()


def stop():
    with open(AppState.proc_ids_path, "r") as f:
        procs = json.loads(f.read())
    electrumsv_node.stop()

    if len(procs) != 0:
        for proc_id in procs:
            subprocess.run(f"taskkill.exe /PID {proc_id} /T /F")

    with open(AppState.proc_ids_path, "w") as f:
        f.write(json.dumps({}))
    print("stack terminated")


def node():
    def cast_str_int_args_to_int():
        int_indices = []
        for index, arg in enumerate(AppState.node_args):
            if arg.isdigit():
                int_indices.append(index)

        for i in int_indices:
            AppState.node_args[i] = int(AppState.node_args[i])

    cast_str_int_args_to_int()
    assert electrumsv_node.is_running(), (
        "bitcoin node must be running to respond to rpc methods. "
        "try: electrumsv-sdk start --node"
    )

    if AppState.node_args[0] in ["--help", "-h"]:
        AppState.node_args[0] = "help"

    result = electrumsv_node.call_any(AppState.node_args[0], *AppState.node_args[1:])
    print(result.json()["result"])


def status():
    status = AppState.get_status()
    logger.debug(f"status={status}")


def reset():
    AppState.load_repo_paths()
    reset_node()
    reset_electrumx()

    AppState.required_dependencies_set.add(AppState.ELECTRUMSV_NODE)
    AppState.required_dependencies_set.add(AppState.ELECTRUMX)
    AppState.required_dependencies_set.add(AppState.ELECTRUMSV)
    start()
    logger.debug("allowing time for the electrumsv daemon to boot up - standby...")
    time.sleep(7)
    reset_electrumsv_wallet()
    stop()
