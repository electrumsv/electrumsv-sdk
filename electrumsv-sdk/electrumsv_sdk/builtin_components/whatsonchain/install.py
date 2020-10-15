import os
import subprocess
import sys

from electrumsv_sdk.components import ComponentName
from electrumsv_sdk.utils import checkout_branch, make_shell_script_for_component


def fetch_whatsonchain(app_state, url="https://github.com/AustEcon/woc-explorer.git",
                       branch=''):
    if not app_state.woc_dir.exists():
        os.makedirs(app_state.woc_dir, exist_ok=True)
        os.chdir(app_state.depends_dir)
        subprocess.run(f"git clone {url}", shell=True, check=True)

        os.chdir(app_state.woc_dir)
        checkout_branch(branch)

    os.chdir(app_state.woc_dir)
    process = subprocess.Popen("call npm install\n" if sys.platform == "win32"
                               else "npm install\n",
                               shell=True)
    process.wait()
    process = subprocess.Popen("call npm run-script build\n" if sys.platform == "win32"
                               else "npm run-script build\n",
                               shell=True)
    process.wait()


def generate_run_script_whatsonchain(app_state):
    app_state.init_run_script_dir()

    commandline_string1 = f"cd {app_state.woc_dir}\n"
    commandline_string2 = f"call npm start\n" if sys.platform == "win32" else f"npm start\n"
    separate_lines = [commandline_string1, commandline_string2]
    make_shell_script_for_component(ComponentName.WHATSONCHAIN,
        commandline_string=None, env_vars=None, multiple_lines=separate_lines)
