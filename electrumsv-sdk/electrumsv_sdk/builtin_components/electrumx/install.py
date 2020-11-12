import logging
import os
import subprocess
import sys
from pathlib import Path

from . import env
from electrumsv_sdk.utils import checkout_branch, is_remote_repo, get_directory_name

DEFAULT_PORT_ELECTRUMX = 51001
COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def configure_paths(app_state, repo, branch):
    if is_remote_repo(repo):
        app_state.component_source_dir = app_state.remote_repos_dir.joinpath("electrumx")
    else:
        logger.debug(f"Tergetting local repo: {COMPONENT_NAME} at {repo}")
        assert Path(repo).exists(), f"the path {repo} does not exist!"
        if branch != "":
            checkout_branch(branch)
        app_state.component_source_dir = Path(repo)

    if not app_state.component_datadir:
        app_state.component_datadir, app_state.component_id = \
            app_state.get_component_datadir(COMPONENT_NAME)
    app_state.component_port = app_state.get_component_port(DEFAULT_PORT_ELECTRUMX, COMPONENT_NAME,
        app_state.component_id)

    # env vars take precedence for port and dbdir
    if env.ELECTRUMX_PORT:
        app_state.component_port = env.ELECTRUMX_PORT


def fetch_electrumx(app_state, url, branch):
    # Todo - make this generic with electrumsv
    """3 possibilities:
    (dir doesn't exists) -> install
    (dir exists, url matches)
    (dir exists, url does not match - it's a forked repo)
    """
    if not app_state.component_source_dir.exists():
        logger.debug(f"Installing electrumx (url={url})")

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
            logger.debug(f"Electrumx is already installed (url={url})")
            subprocess.run(f"git pull", shell=True, check=True)
            checkout_branch(branch)

        if result.stdout.strip() != url:
            existing_fork = app_state.component_source_dir
            logger.debug(f"Alternate fork of electrumx is already installed")
            logger.debug(f"Moving existing fork (to '{existing_fork}.bak')")
            logger.debug(f"Installing electrumsv (url={url})")
            os.rename(
                app_state.component_source_dir,
                app_state.component_source_dir.with_suffix(".bak"),
            )
            # not app_state.electrumx_dir.exists() == True -> clones repo

    if not app_state.component_source_dir.exists():
        os.chdir(app_state.remote_repos_dir)
        subprocess.run(f"git clone {url}", shell=True, check=True)

        os.chdir(app_state.component_source_dir)
        checkout_branch(branch)


def packages_electrumx(app_state, url, branch):
    """plyvel wheels are not available on windows so it is swapped out for plyvel-win32 to
    make it work"""
    os.chdir(app_state.component_source_dir)
    checkout_branch(branch)
    requirements_path = app_state.component_source_dir.joinpath('requirements.txt')

    if sys.platform in ['linux', 'darwin']:
        process = subprocess.Popen(
            f"{app_state.python} -m pip install -r {requirements_path}", shell=True)
        process.wait()

    elif sys.platform == 'win32':
        temp_requirements = app_state.component_source_dir.joinpath('requirements-temp.txt')
        packages = []
        with open(requirements_path, 'r') as f:
            for line in f.readlines():
                if line.strip() == 'plyvel':
                    continue
                packages.append(line)
        packages.append('plyvel-win32')
        with open(temp_requirements, 'w') as f:
            f.writelines(packages)
        process = subprocess.Popen(
            f"{app_state.python} -m pip install --user -r {temp_requirements}", shell=True)
        process.wait()
        os.remove(temp_requirements)


def generate_run_script(app_state):
    os.makedirs(app_state.shell_scripts_dir, exist_ok=True)
    os.chdir(app_state.shell_scripts_dir)
    env_var_setter = 'set' if sys.platform == 'win32' else 'export'

    lines = [
        f"{env_var_setter} SERVICES="f"{f'tcp://:{app_state.component_port},rpc://'}",
        f"{env_var_setter} DB_DIRECTORY={app_state.component_datadir}",
        f"{env_var_setter} DAEMON_URL={env.DAEMON_URL}",
        f"{env_var_setter} DB_ENGINE={env.DB_ENGINE}",
        f"{env_var_setter} COIN={env.COIN}",
        f"{env_var_setter} COST_SOFT_LIMIT={env.COST_SOFT_LIMIT}",
        f"{env_var_setter} COST_HARD_LIMIT={env.COST_HARD_LIMIT}",
        f"{env_var_setter} MAX_SEND={env.MAX_SEND}",
        f"{env_var_setter} LOG_LEVEL={env.LOG_LEVEL}",
        f"{env_var_setter} NET={env.NET}",
        f"{env_var_setter} ALLOW_ROOT={env.ALLOW_ROOT}",
        f"{app_state.python} {app_state.component_source_dir.joinpath('electrumx_server')}"
    ]
    app_state.make_shell_script_for_component(list_of_shell_commands=lines,
        component_name=COMPONENT_NAME)
