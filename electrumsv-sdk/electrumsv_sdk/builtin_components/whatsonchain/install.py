import logging
import os
import subprocess
import sys

from electrumsv_sdk.utils import checkout_branch, get_directory_name

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def fetch_whatsonchain(app_state, url="https://github.com/AustEcon/woc-explorer.git",
                       branch=''):
    if not app_state.src_dir.exists():
        os.makedirs(app_state.src_dir, exist_ok=True)
        os.chdir(app_state.remote_repos_dir)
        subprocess.run(f"git clone {url}", shell=True, check=True)

        os.chdir(app_state.src_dir)
        checkout_branch(branch)


def packages_whatsonchain(app_state):
    os.chdir(app_state.src_dir)
    process = subprocess.Popen("npm install", shell=True)
    process.wait()
    process = subprocess.Popen("npm run-script build", shell=True)
    process.wait()


def generate_run_script(app_state):
    os.makedirs(app_state.shell_scripts_dir, exist_ok=True)
    os.chdir(app_state.shell_scripts_dir)
    line1 = f"cd {app_state.src_dir}"
    line2 = f"call npm start" if sys.platform == "win32" else f"npm start"
    app_state.make_shell_script_for_component(list_of_shell_commands=[line1, line2],
        component_name=COMPONENT_NAME)
