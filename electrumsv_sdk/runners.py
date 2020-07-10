import subprocess
import sys

from .config import Config


def run_electrumsv_node():
    from electrumsv_node import electrumsv_node

    electrumsv_node.start()


def run_electrumx_server():
    electrumx_env_vars = {
        "DB_DIRECTORY": Config.depends_dir_electrumx_data.__str__(),
        "DAEMON_URL": "http://rpcuser:rpcpassword@127.0.0.1:18332",
        "DB_ENGINE": "leveldb",
        "SERVICES": "tcp://:51001,rpc://",
        "COIN": "BitcoinSV",
        "COST_SOFT_LIMIT": "0",
        "COST_HARD_LIMIT": "0",
        "MAX_SEND": "10000000",
        "LOG_LEVEL": "debug",
        "NET": "regtest",
    }
    if sys.platform == "win32":
        electrumx_server_script = Config.run_scripts_dir.joinpath("electrumx.bat")
    else:
        electrumx_server_script = Config.run_scripts_dir.joinpath("electrumx.sh")

    process = subprocess.Popen(f"{electrumx_server_script}", creationflags=subprocess.CREATE_NEW_CONSOLE)
    return process


def run_electrumsv_daemon():
    esv_script = Config.depends_dir_electrumsv.joinpath("electrum-sv").__str__()
    process = subprocess.Popen(
        f"{sys.executable} {esv_script} --regtest daemon --v=debug "
        f"--file-logging "
        f"--restapi --server=127.0.0.1:51001:t", creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    return process
