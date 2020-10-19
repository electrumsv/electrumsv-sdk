import logging
import os
import subprocess
import sys
from pathlib import Path

from electrumsv_sdk.components import ComponentOptions
from electrumsv_sdk.utils import is_remote_repo, checkout_branch, \
    make_shell_script_for_component, get_directory_name, get_component_port

DEFAULT_PORT_ELECTRUMSV = 9999
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def configure_paths(app_state, repo, branch):
    if is_remote_repo(repo):
        app_state.component_source_dir = app_state.remote_repos_dir.joinpath("electrumsv")
    else:
        logger.debug(f"Installing local dependency {COMPONENT_NAME} at {repo}")
        assert Path(repo).exists(), f"the path {repo} does not exist!"
        if branch != "":
            checkout_branch(branch)
        app_state.component_source_dir = Path(repo)

    app_state.electrumsv_requirements_path = (
        app_state.component_source_dir.joinpath("contrib/deterministic-build/requirements.txt")
    )
    app_state.electrumsv_binary_requirements_path = (
        app_state.component_source_dir.joinpath(
            "contrib/deterministic-build/requirements-binaries.txt")
    )
    app_state.component_port = get_component_port(DEFAULT_PORT_ELECTRUMSV)
    app_state.component_datadir = app_state.component_store.get_component_data_dir(COMPONENT_NAME)


def fetch_electrumsv(app_state, url, branch):
    # Todo - make this generic with electrumx
    """3 possibilities:
    (dir doesn't exists) -> install
    (dir exists, url matches)
    (dir exists, url does not match - it's a forked repo)
    """
    if not app_state.component_source_dir.exists():
        logger.debug(f"Installing electrumsv (url={url})")
        os.chdir(app_state.remote_repos_dir)
        subprocess.run(f"git clone {url}", shell=True, check=True)

    elif app_state.component_source_dir.exists():
        os.chdir(app_state.component_source_dir)
        result = subprocess.run(
            f"git config --get remote.origin.url",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.stdout.strip() == url:
            logger.debug(f"Electrumsv is already installed (url={url})")
            checkout_branch(branch)
            subprocess.run(f"git pull", shell=True, check=True)
        if result.stdout.strip() != url:
            existing_fork = app_state.component_source_dir
            logger.debug(f"Alternate fork of electrumsv is already installed")
            logger.debug(f"Moving existing fork (to '{existing_fork}.bak')")
            logger.debug(f"Installing electrumsv (url={url})")
            os.rename(
                app_state.component_source_dir,
                app_state.component_source_dir.with_suffix(".bak"),
            )


def packages_electrumsv(app_state, url, branch):
    # Todo - provide a python helper tool for supplying a list of installation commands (
    #  f-strings with app_state.python)
    os.chdir(app_state.component_source_dir)
    checkout_branch(branch)

    if sys.platform == 'win32':
        cmd1 = f"{app_state.python} -m pip install --user --upgrade -r " \
               f"{app_state.electrumsv_requirements_path}"
        cmd2 = f"{app_state.python} -m pip install --user --upgrade -r " \
               f"{app_state.electrumsv_binary_requirements_path}"
    elif sys.platform in ['linux', 'darwin']:
        cmd1 = f"sudo {app_state.python} -m pip install --upgrade -r " \
               f"{app_state.electrumsv_requirements_path}"
        cmd2 = f"sudo {app_state.python} -m pip install --upgrade -r " \
               f"{app_state.electrumsv_binary_requirements_path}"

    process1 = subprocess.Popen(cmd1, shell=True)
    process1.wait()
    process2 = subprocess.Popen(cmd2, shell=True)
    process2.wait()


def add_esv_default_args(commandline_string, esv_data_dir, port):
    commandline_string += (
        f" --portable --dir {esv_data_dir} "
        f"--regtest daemon -dapp restapi --v=debug --file-logging "
        f"--restapi --restapi-port={port} --server=127.0.0.1:51001:t "
    )
    return commandline_string


def make_esv_custom_script(base_cmd, env_vars, component_args, esv_data_dir):
    """if cli args are supplied to electrumsv then it gives a "clean slate" (discarding the default
    configuration. (but ensures that the --dir and --restapi flags are set if not already)"""
    commandline_string = base_cmd
    additional_args = " ".join(component_args)
    commandline_string += " " + additional_args
    if "--dir" not in component_args:
        commandline_string += " " + f"--dir {esv_data_dir}"

    # so that polling works
    if "--restapi" not in component_args:
        commandline_string += " " + f"--restapi"

    make_shell_script_for_component(COMPONENT_NAME, commandline_string, env_vars)


def make_esv_daemon_script(base_cmd, env_vars, esv_data_dir, port):
    commandline_string = base_cmd + (
        f" --portable --dir {esv_data_dir} "
        f"--regtest daemon -dapp restapi --v=debug --file-logging "
        f"--restapi --restapi-port={port} --server=127.0.0.1:51001:t --restapi-user rpcuser"
        f" --restapi-password= "
    )
    make_shell_script_for_component(COMPONENT_NAME, commandline_string, env_vars)


def make_esv_gui_script(base_cmd, env_vars, esv_data_dir, port):
    commandline_string = base_cmd + (
        f" gui --regtest --restapi --restapi-port={port} "
        f"--v=debug --file-logging --server=127.0.0.1:51001:t --dir {esv_data_dir}"
    )
    make_shell_script_for_component(COMPONENT_NAME, commandline_string, env_vars)


def generate_run_scripts_electrumsv(app_state):
    """makes both the daemon script and a script for running the GUI"""
    app_state.init_run_script_dir()
    path_to_dapp_example_apps = app_state.component_source_dir.joinpath("examples/applications")
    esv_env_vars = {"PYTHONPATH": str(path_to_dapp_example_apps)}
    esv_script = str(app_state.component_source_dir.joinpath("electrum-sv"))
    esv_data_dir = app_state.component_datadir
    port = app_state.component_port
    component_args = \
        app_state.component_args if len(app_state.component_args) != 0 else None

    logger.debug(f"esv_data_dir = {esv_data_dir}")

    base_cmd = (f"{app_state.python} {esv_script}")
    if component_args:
        make_esv_custom_script(base_cmd, esv_env_vars, component_args, esv_data_dir)
    elif not app_state.global_cli_flags[ComponentOptions.GUI]:
        make_esv_daemon_script(base_cmd, esv_env_vars, esv_data_dir, port)
    else:
        make_esv_gui_script(base_cmd, esv_env_vars, esv_data_dir, port)
