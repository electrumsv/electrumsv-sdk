import subprocess
from subprocess import CREATE_NEW_CONSOLE
import sys

from .config import Config

from subprocess import Popen, CREATE_NEW_CONSOLE


def run_electrumsv_daemon():
    print()
    print()
    print("running electrumsv daemon...")
    print("----------------------------")
    esv_script = Config.depends_dir_electrumsv.joinpath("electrum-sv").__str__()
    subprocess.Popen(
        f"start cmd /K {sys.executable} {esv_script} --regtest daemon --v=debug "
        f"--file-logging "
        f"--restapi --server=127.0.0.1:51001:t",
        shell=True
    )
