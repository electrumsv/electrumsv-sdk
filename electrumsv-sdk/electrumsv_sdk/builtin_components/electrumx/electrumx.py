from electrumsv_sdk.components import ComponentOptions
from electrumsv_sdk.utils import is_remote_repo

from .install import configure_paths_and_maps_electrumx, fetch_electrumx, packages_electrumx, \
    generate_run_script_electrumx


def install(app_state):
    """--repo and --branch flags affect the behaviour of the 'fetch' step"""
    repo = app_state.start_options[ComponentOptions.REPO]
    branch = app_state.start_options[ComponentOptions.BRANCH]

    # 1) configure_paths_and_maps
    configure_paths_and_maps_electrumx(app_state, repo, branch)

    # 2) fetch (as needed)
    if is_remote_repo(repo):
        repo = "https://github.com/kyuupichan/electrumx.git"
        fetch_electrumx(app_state, repo, branch)

    # 3) pip install (or npm install) packages/dependencies
    packages_electrumx(app_state, repo, branch)

    # 4) generate run script
    generate_run_script_electrumx(app_state)


def start(app_state):
    pass


def stop(app_state):
    pass


def reset(app_state):
    pass


def status_check(app_state):
    pass
