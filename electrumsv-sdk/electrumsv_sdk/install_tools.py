import os
import shlex
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

    if not Config.electrumsv_dir.exists():
        os.chdir(Config.depends_dir.__str__())
        subprocess.run(f"git clone {url}", shell=True, check=True)
        checkout_branch(branch)
        subprocess.run(f"{sys.executable} -m pip install -r {Config.electrumsv_requirements_path}")
        subprocess.run(
            f"{sys.executable} -m pip install -r {Config.electrumsv_binary_requirements_path}"
        )
    generate_run_script_electrumsv()

def generate_run_script_electrumsv():
    create_if_not_exist(Config.run_scripts_dir)
    os.chdir(Config.run_scripts_dir)
    path_to_dapp_example_apps = Config.electrumsv_dir.joinpath("examples").joinpath("applications")
    electrumsv_env_vars = {
        'PYTHONPATH': path_to_dapp_example_apps.__str__(),
    }
    esv_script = Config.electrumsv_dir.joinpath("electrum-sv").__str__()

    commandline_string = (f"{sys.executable} {esv_script} --regtest daemon -dapp restapi "
                          f"--v=debug --file-logging --restapi --server=127.0.0.1:51001:t "
                          f"--portable")

    commandline_string_split = shlex.split(commandline_string, posix=0)

    def make_bat_file(filename):
        open(filename, 'w').close()
        with open(filename, 'a') as f:
            f.write("@echo off\n")
            for key, val in electrumsv_env_vars.items():
                f.write(f"set {key}={val}\n")
            for subcmd in commandline_string_split:
                f.write(f"{subcmd}" + " ")
            f.write("\n")
            f.write("pause\n")

    def make_bash_file(filename):
        open(filename, 'w').close()
        with open(filename, 'a') as f:
            f.write("#!/bin/bash\n")
            f.write("set echo off\n")
            for key, val in electrumsv_env_vars.items():
                f.write(f"export {key}={val}\n")
            for subcmd in commandline_string_split:
                f.write(f"{subcmd}" + " ")
            f.write("\n")
            f.write('read -s -n 1 -p "Press any key to continue" . . .\n')
            f.write('exit')
    if sys.platform == 'win32':
        make_bat_file("electrumsv.bat")
    elif sys.platform in ['linux', 'darwin']:
        make_bash_file("electrumsv.sh")


def generate_run_script_electrumx():
    create_if_not_exist(Config.run_scripts_dir)
    os.chdir(Config.run_scripts_dir)
    electrumx_env_vars = {
        'DB_DIRECTORY': Config.electrumx_data_dir.__str__(),
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
                '"' + f"{Config.electrumx_dir.joinpath('electrumx_server')}" + '"\n')
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
                '"' + f"{Config.electrumx_dir.joinpath('electrumx_server')}" + '"\n')
            f.write('read -s -n 1 -p "Press any key to continue" . . .\n')
            f.write('exit')

    if sys.platform == 'win32':
        make_bat_file("electrumx.bat")
    elif sys.platform in ['linux', 'darwin']:
        make_bash_file("electrumx.sh")

def install_electrumx(url, branch):

    if not Config.electrumx_dir.exists():
        create_if_not_exist(Config.electrumx_dir.__str__())
        create_if_not_exist(Config.electrumx_data_dir.__str__())
        os.chdir(Config.depends_dir.__str__())
        subprocess.run(f"git clone {url}", shell=True, check=True)
        checkout_branch(branch)
        generate_run_script_electrumx()


def install_electrumsv_node():
    subprocess.run(f"{sys.executable} -m pip install electrumsv-node", shell=True, check=True)
