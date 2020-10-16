import subprocess


def fetch_node(app_state):
    subprocess.run(f"{app_state.python} -m pip install electrumsv-node", shell=True, check=True)
