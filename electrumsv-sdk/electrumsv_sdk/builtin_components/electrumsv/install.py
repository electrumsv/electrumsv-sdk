import logging
import os
import subprocess
import sys
from pathlib import Path

from electrumsv_sdk.components import ComponentOptions
from electrumsv_sdk.utils import is_remote_repo, checkout_branch, \
    get_directory_name

from . import env

DEFAULT_PORT = 9999
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def configure_paths(app_state, repo, branch):
    if is_remote_repo(repo):
        app_state.component_source_dir = app_state.remote_repos_dir.joinpath("electrumsv")
    else:
        logger.debug(f"Targetting local repo {COMPONENT_NAME} at {repo}")
        assert Path(repo).exists(), f"the path {repo} does not exist!"
        if branch != "":
            checkout_branch(branch)
        app_state.component_source_dir = Path(repo)

    if not app_state.component_datadir:
        app_state.component_datadir, app_state.component_id = \
            app_state.get_component_datadir(COMPONENT_NAME)
    app_state.component_port = app_state.get_component_port(DEFAULT_PORT,
        COMPONENT_NAME, app_state.component_id)


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
            logger.debug(f"ElectrumSV is already installed (url={url})")
            subprocess.run(f"git pull", shell=True, check=True)
            checkout_branch(branch)
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

    electrumsv_requirements_path = (
        app_state.component_source_dir.joinpath("contrib/deterministic-build/requirements.txt")
    )
    electrumsv_binary_requirements_path = (
        app_state.component_source_dir.joinpath(
            "contrib/deterministic-build/requirements-binaries.txt")
    )

    if sys.platform == 'win32':
        cmd1 = f"{app_state.python} -m pip install --user --upgrade -r " \
               f"{electrumsv_requirements_path}"
        cmd2 = f"{app_state.python} -m pip install --user --upgrade -r " \
               f"{electrumsv_binary_requirements_path}"
    elif sys.platform in ['linux', 'darwin']:
        cmd1 = f"{app_state.python} -m pip install --user --upgrade -r " \
               f"{electrumsv_requirements_path}"
        cmd2 = f"{app_state.python} -m pip install --user --upgrade -r " \
               f"{electrumsv_binary_requirements_path}"

    process1 = subprocess.Popen(cmd1, shell=True)
    process1.wait()
    process2 = subprocess.Popen(cmd2, shell=True)
    process2.wait()


def generate_run_script(app_state):
    """
    The electrumsv component type can be executed in 1 of 3 ways:
     1) custom script (if args are supplied to the right-hand-side of <component_name>)
     2) daemon script
     3) gui script for running in GUI mode

    NOTE: This is about as complex as it gets!
    """
    esv_launcher = str(app_state.component_source_dir.joinpath("electrum-sv"))
    esv_datadir = app_state.component_datadir
    port = app_state.component_port
    logger.debug(f"esv_datadir = {esv_datadir}")

    # custom script (user-specified arguments are fed to ESV)
    component_args = app_state.component_args if len(app_state.component_args) != 0 else None
    if component_args:
        additional_args = " ".join(component_args)
        line1 = f"{app_state.python} {esv_launcher} {additional_args}"
        if "--dir" not in component_args:
            line1 += " " + f"--dir {esv_datadir}"

        lines = [line1]

    # daemon script
    elif not app_state.global_cli_flags[ComponentOptions.GUI]:
        path_to_example_dapps = app_state.component_source_dir.joinpath("examples/applications")
        line1 = f"set PYTHONPATH={path_to_example_dapps}"
        if sys.platform in {'linux', 'darwin'}:
            line1 = f"export PYTHONPATH={path_to_example_dapps}"

        line2 = (
            f"{app_state.python} {esv_launcher} --portable --dir {esv_datadir} --regtest daemon "
            f"-dapp restapi --v=debug --file-logging --restapi --restapi-port={port} "
            f"--server={env.ELECTRUMX_HOST}:{env.ELECTRUMX_PORT}:t --restapi-user rpcuser "
            f"--restapi-password= "
        )
        lines = [line1, line2]

    # GUI script
    else:
        line1 = (
            f"{app_state.python} {esv_launcher} gui --regtest --restapi --restapi-port={port} "
            f"--v=debug --file-logging --server={env.ELECTRUMX_HOST}:{env.ELECTRUMX_PORT}:t "
            f"--dir {esv_datadir}"
        )
        lines = [line1]
    app_state.make_shell_script_for_component(list_of_shell_commands=lines,
        component_name=COMPONENT_NAME)
