import os
import subprocess
import sys
from pathlib import Path
from .config import Config
from .utils import checkout_branch


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


def install_electrumsv(url, branch):
    # Note - this is only so that it works "out-of-the-box". But for development
    # should use a dedicated electrumsv repo and specify it via cli arguments (not implemented)

    if not Config.depends_dir_electrumsv.exists():
        create_if_not_exist(Config.depends_dir_electrumsv)
        os.chdir(Config.depends_dir.__str__())
        subprocess.run(f"git clone {url}", shell=True, check=True)
        checkout_branch(branch)
        subprocess.run(f"{sys.executable} -m pip install -r {Config.depends_dir_electrumsv_req}")
        subprocess.run(
            f"{sys.executable} -m pip install -r {Config.depends_dir_electrumsv_req_bin}"
        )

def generate_run_script_electrumx():
    create_if_not_exist(Config.run_scripts_dir)
    os.chdir(Config.run_scripts_dir)
    electrumx_env_vars = {
        'DB_DIRECTORY': Config.depends_dir_electrumx_data.__str__(),
        'DAEMON_URL': 'http://rpcuser:rpcpassword@127.0.0.1:18332',
        'DB_ENGINE': 'leveldb',
        'SERVICES': 'tcp://:51001,rpc://',
        'COIN': 'BitcoinSV',
        'COST_SOFT_LIMIT': '0',
        'COST_HARD_LIMIT': '0',
        'MAX_SEND': '10000000',
        'LOG_LEVEL': 'debug',
        'NET': 'regtest',
    }

    def make_bat_file(filename):
        open(filename, 'w').close()
        with open(filename, 'a') as f:
            f.write("@echo off\n")
            for key, val in electrumx_env_vars.items():
                f.write(f"set {key}={val}\n")
            f.write(
                '"' + f"{sys.executable}" + '"' + " " +
                '"' + f"{Config.depends_dir_electrumx.joinpath('electrumx_server')}" + '"\n')
            f.write("pause\n")

    def make_bash_file(filename):
        open(filename, 'w').close()
        with open(filename, 'a') as f:
            f.write("#!/bin/bash\n")
            f.write("set echo off\n")
            for key, val in electrumx_env_vars.items():
                f.write(f"export {key}={val}\n")
            f.write(
                '"' + f"{sys.executable}" + '"' + " " +
                '"' + f"{Config.depends_dir_electrumx.joinpath('electrumx_server')}" + '"\n')
            f.write('read -s -n 1 -p "Press any key to continue" . . .\n')
            f.write('exit')

    if sys.platform == 'win32':
        make_bat_file("electrumx.bat")
    elif sys.platform in ['linux', 'darwin']:
        make_bash_file("electrumx.sh")

def install_electrumx(url, branch):

    if not Config.depends_dir_electrumx.exists():
        create_if_not_exist(Config.depends_dir_electrumx.__str__())
        create_if_not_exist(Config.depends_dir_electrumx_data.__str__())
        os.chdir(Config.depends_dir.__str__())
        subprocess.run(f"git clone {url}", shell=True, check=True)
        checkout_branch(branch)

        # use modified requirements to exclude the plyvel install (problematic on windows)
        subprocess.run(f"{sys.executable} -m pip install -r {Config.sdk_requirements_electrumx}")
        generate_run_script_electrumx()


def install_electrumsv_node():
    subprocess.run(f"{sys.executable} -m pip install electrumsv-node", shell=True, check=True)
