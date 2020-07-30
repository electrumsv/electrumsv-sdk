import datetime
import os
import shlex
import subprocess
import sys
from pathlib import Path

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

def checkout_branch(branch: str):
    if branch != "":
        subprocess.run(f"git checkout {branch}", shell=True, check=True)

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


def make_bat_file(filename, commandline_string_split, env_vars):
    open(filename, "w").close()
    with open(filename, "a") as f:
        f.write("@echo off\n")
        for key, val in env_vars.items():
            f.write(f"set {key}={val}\n")
        for subcmd in commandline_string_split:
            f.write(f"{subcmd}" + " ")
        f.write("\n")
        f.write("pause\n")


def make_bash_file(filename, commandline_string_split, env_vars):
    open(filename, "w").close()
    with open(filename, "a") as f:
        f.write("#!/bin/bash\n")
        f.write("set echo off\n")
        for key, val in env_vars.items():
            f.write(f"export {key}={val}\n")
        for subcmd in commandline_string_split:
            f.write(f"{subcmd}" + " ")
        f.write("\n")
        f.write('read -s -n 1 -p "Press any key to continue" . . .\n')
        f.write("exit")


def make_esv_daemon_script(esv_script, electrumsv_env_vars):
    commandline_string = (
        f"{sys.executable} {esv_script} --regtest daemon -dapp restapi "
        f"--v=debug --file-logging --restapi --server=127.0.0.1:51001:t "
        f"--portable"
    )

    if sys.platform == "win32":
        commandline_string_split = shlex.split(commandline_string, posix=0)
        make_bat_file("electrumsv.bat", commandline_string_split, electrumsv_env_vars)

    elif sys.platform in ["linux", "darwin"]:
        commandline_string_split = shlex.split(commandline_string, posix=1)
        make_bash_file("electrumsv.sh", commandline_string_split, electrumsv_env_vars)


def make_esv_gui_script(esv_script, electrumsv_env_vars):
    commandline_string = (
        f"{sys.executable} {esv_script} --regtest --v=debug --file-logging "
        f"--server=127.0.0.1:51001:t --portable"
    )

    if sys.platform == "win32":
        commandline_string_split = shlex.split(commandline_string, posix=0)
        make_bat_file("electrumsv-gui.bat", commandline_string_split, electrumsv_env_vars)

    elif sys.platform in ["linux", "darwin"]:
        commandline_string_split = shlex.split(commandline_string, posix=1)
        make_bash_file("electrumsv-gui.sh", commandline_string_split, electrumsv_env_vars)

def get_str_datetime():
    return datetime.datetime.now().strftime(TIME_FORMAT)
