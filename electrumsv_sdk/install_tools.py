import json
import os
import subprocess
import sys
from pathlib import Path

# most of the directories will be hard-coded relative to the position of this file
# I'd rather not over-complicate things by trying to give everything a variable name
# and making it easy to refactor... Can do that as/when it is deemed necessary.
from electrumsv_sdk.config import Config


def create_if_not_exist(path):
    path = Path(path)
    root = Path(path.parts[0])  # Root
    cur_dir = Path(root)
    for part in path.parts:
        if Path(part) != root:
            cur_dir = cur_dir.joinpath(part)
        if cur_dir.exists():
            continue
        else:
            os.mkdir(cur_dir)
            print(f"created '{cur_dir}' successfully")


def install_electrumsv():
    # Note - this is only so that it works "out-of-the-box". But for development
    # should use a dedicated electrumsv repo and specify it via cli arguments (not implemented)
    depends_dir_electrumsv_req = Config.depends_dir_electrumsv.joinpath(
        'contrib').joinpath('deterministic-build').joinpath('requirements.txt')
    depends_dir_electrumsv_req_bin = Config.depends_dir_electrumsv.joinpath(
        'contrib').joinpath('deterministic-build').joinpath('requirements-binaries.txt')

    create_if_not_exist(Config.depends_dir)
    create_if_not_exist(Config.depends_dir_electrumsv)

    os.chdir(Config.depends_dir.__str__())
    if not Config.depends_dir_electrumsv.exists():
        subprocess.run(f"git clone https://github.com/electrumsv/electrumsv.git", shell=True)
        subprocess.run(f"{sys.executable} -m pip install -r {depends_dir_electrumsv_req}")
        subprocess.run(f"{sys.executable} -m pip install -r {depends_dir_electrumsv_req_bin}")


def install_electrumx():
    electrumx_server_exe = Config.depends_dir_electrumx.joinpath('electrumx').joinpath('electrumx_server')

    create_if_not_exist(Config.depends_dir.__str__())
    create_if_not_exist(Config.depends_dir_electrumx.__str__())
    create_if_not_exist(Config.depends_dir_electrumx_data.__str__())

    os.chdir(Config.depends_dir.__str__())
    if not Config.depends_dir_electrumx.exists():
        subprocess.run(f"git clone https://github.com/kyuupichan/electrumx.git", shell=True)

    def make_bat_file(filename, electrumx_env_vars):
        open(filename, 'w').close()
        with open(filename, 'a') as f:
            f.write("@echo off\n")
            for key, value in electrumx_env_vars.items():
                f.write(f"set {key}={value}\n")
            f.write(
                '"' + f"{sys.executable}" + '"' + " " + '"' + f"{electrumx_server_exe}" + '"\n')
            f.write("pause\n")

    def make_bash_file(filename, electrumx_env_vars):
        open(filename, 'w').close()
        with open(filename, 'a') as f:
            f.write("#!/bin/bash\n")
            f.write("set echo off\n")
            for key, value in electrumx_env_vars.items():
                f.write(f"export {key}={value}\n")
            f.write(
                '"' + f"{sys.executable}" + '"' + " " + '"' + f"{electrumx_server_exe}" + '"\n')
            f.write('read -s -n 1 -p "Press any key to continue" . . .\n')
            f.write('exit')

    electrumx_env_vars = {
        'DB_DIRECTORY': Config.depends_dir_electrumx_data,
        'DAEMON_URL': "http://rpcuser:rpcpassword@127.0.0.1:18332",
        'DB_ENGINE': 'leveldb',
        'SERVICES': "tcp://:51001,rpc://",
        'COIN': 'BitcoinSV',
        'COST_SOFT_LIMIT':  0,
        'COST_HARD_LIMIT': 0,
        'MAX_SEND': 10000000,
        'LOG_LEVEL': 'debug',
        'NET': 'regtest',
    }

    if sys.platform == 'win32':
        make_bat_file("electrumx.bat", electrumx_env_vars)
    elif sys.platform in ['linux', 'darwin']:
        make_bash_file("electrumx.sh", electrumx_env_vars)

def install_electrumsv_node():
    subprocess.run(f"{sys.executable} -m pip install electrumsv-node", shell=True, check=True)
