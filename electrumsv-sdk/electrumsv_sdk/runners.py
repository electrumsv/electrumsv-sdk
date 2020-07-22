import json
import logging
import subprocess
import sys
import time

from electrumsv_node import electrumsv_node
from electrumsv_sdk.reset import reset_node, reset_electrumx, reset_electrumsv_wallet

from .config import Config


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H-%M-%S",
)
logger = logging.getLogger("runners")


def run_electrumsv_node():
    from electrumsv_node import electrumsv_node

    electrumsv_node.start()


def run_electrumx_server():
    logger.debug(f"starting RegTest electrumx server...")
    if sys.platform == "win32":
        electrumx_server_script = Config.run_scripts_dir.joinpath("electrumx.bat")
    else:
        electrumx_server_script = Config.run_scripts_dir.joinpath("electrumx.sh")

    process = subprocess.Popen(
        f"{electrumx_server_script}", creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    return process


def disable_rest_api_authentication():
    path_to_config = Config.electrumsv_regtest_config_dir.__str__()

    with open(path_to_config, "r") as f:
        config = json.load(f)
        config["rpcpassword"] = ""
        config["rpcuser"] = "user"

    with open(path_to_config, "w") as f:
        f.write(json.dumps(config, indent=4))


def start_and_stop_ESV(electrumsv_server_script):
    # Ugly hack (first time run through need to start then stop ESV wallet to make config files)
    logger.debug("starting RegTest electrumsv daemon for the first time - initializing wallet ")
    process = subprocess.Popen(f"{electrumsv_server_script}",
        creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(5)
    subprocess.run(f"taskkill.exe /PID {process.pid} /T /F")


def run_electrumsv_daemon(is_first_run=False):
    """Todo - this currently uses ugly hacks with starting and stopping the ESV wallet in order to:
    1) generate the config files (so that it can be directly edited) - would be obviated by
    fixing this: https://github.com/electrumsv/electrumsv/issues/111
    2) newly created wallet doesn't seem to be fully useable until after stopping the daemon."""
    if sys.platform == "win32":
        electrumsv_server_script = Config.run_scripts_dir.joinpath("electrumsv.bat")
    else:
        electrumsv_server_script = Config.run_scripts_dir.joinpath("electrumsv.sh")

    try:
        disable_rest_api_authentication()

        logger.debug(f"starting RegTest electrumsv daemon...")
        process = subprocess.Popen(
            f"{electrumsv_server_script}", creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        if is_first_run:
            time.sleep(5)
            reset_electrumsv_wallet()  # create first-time wallet
            time.sleep(2)
            subprocess.run(f"taskkill.exe /PID {process.pid} /T /F")
            return run_electrumsv_daemon(is_first_run=False)

        return process
    except FileNotFoundError:  # is_first_run = True
        start_and_stop_ESV(electrumsv_server_script)  # generates config json file
        disable_rest_api_authentication()  # now this will work
        return run_electrumsv_daemon(is_first_run=True)


def start():
    procs = startup()
    with open(Config.proc_ids_path, 'w') as f:
        f.write(json.dumps(procs))
    Config.save_repo_paths()


def stop():
    with open(Config.proc_ids_path, 'r') as f:
        procs = json.loads(f.read())
    electrumsv_node.stop()

    if len(procs) != 0:
        for proc_id in procs:
            subprocess.run(f"taskkill.exe /PID {proc_id} /T /F")

    with open(Config.proc_ids_path, 'w') as f:
        f.write(json.dumps({}))
    print("stack terminated")

def node():
    def cast_str_int_args_to_int():
        int_indices = []
        for index, arg in enumerate(Config.node_args):
            if arg.isdigit():
                int_indices.append(index)

        for i in int_indices:
            Config.node_args[i] = int(Config.node_args[i])

    cast_str_int_args_to_int()
    assert electrumsv_node.is_running(), "bitcoin node must be running to respond to rpc methods. " \
                                         "try: electrumsv-sdk start --node"

    if Config.node_args[0] in ["--help", "-h"]:
        Config.node_args[0] = "help"

    result = electrumsv_node.call_any(Config.node_args[0], *Config.node_args[1:])
    print(result.json()['result'])

def reset():
    Config.load_repo_paths()
    reset_node()
    reset_electrumx()

    Config.required_dependencies_set.add(Config.ELECTRUMSV_NODE)
    Config.required_dependencies_set.add(Config.ELECTRUMX)
    Config.required_dependencies_set.add(Config.ELECTRUMSV)
    start()
    time.sleep(5)
    reset_electrumsv_wallet()
    stop()


def startup():
    print()
    print()
    print("running stack...")
    procs = []
    if 'electrumsv_node' in Config.required_dependencies_set:
        run_electrumsv_node()

    if 'electrumx' in Config.required_dependencies_set:
        electrumx_process = run_electrumx_server()
        procs.append(electrumx_process.pid)

    if 'electrumsv' in Config.required_dependencies_set:
        esv_process = run_electrumsv_daemon()
        procs.append(esv_process.pid)
    return procs
