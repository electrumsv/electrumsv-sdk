import os
import subprocess
import sys

from electrumsv_sdk.utils import checkout_branch


class Installers:
    def __init__(self, app_state):
        self.app_state = app_state

    def remote_electrumsv(self, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        if not self.app_state.electrumsv_dir.exists():
            print(f"- installing electrumsv (url={url})")
            self.app_state.install_tools.install_electrumsv(url, branch)

        elif self.app_state.electrumsv_dir.exists():
            os.chdir(self.app_state.electrumsv_dir)
            result = subprocess.run(
                f"git config --get remote.origin.url",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.stdout.strip() == url:
                print(f"- electrumsv is already installed (url={url})")
                checkout_branch(branch)
                subprocess.run(f"git pull", shell=True, check=True)
                subprocess.run(
                    f"{sys.executable} -m pip install -r "
                    f"{self.app_state.electrumsv_requirements_path}",
                    shell=True,
                    check=True,
                )
                subprocess.run(
                    f"{sys.executable} -m pip install -r "
                    f"{self.app_state.electrumsv_binary_requirements_path}",
                    shell=True,
                    check=True,
                )
            if result.stdout.strip() != url:
                existing_fork = self.app_state.electrumsv_dir
                print(f"- alternate fork of electrumsv is already installed")
                print(f"- moving existing fork (to '{existing_fork}.bak')")
                print(f"- installing electrumsv (url={url})")
                os.rename(
                    self.app_state.electrumsv_dir,
                    self.app_state.electrumsv_dir.with_suffix(".bak"),
                )
                self.app_state.install_tools.install_electrumsv(url, branch)

        os.makedirs(self.app_state.electrumsv_regtest_wallets_dir, exist_ok=True)

    def local_electrumsv(self, url, branch):
        os.makedirs(self.app_state.electrumsv_regtest_wallets_dir, exist_ok=True)
        self.app_state.install_tools.generate_run_scripts_electrumsv()

    def remote_electrumx(self, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        if not self.app_state.electrumx_dir.exists():
            print(f"- installing electrumx (url={url})")
            self.app_state.install_tools.install_electrumx(url, branch)
        elif self.app_state.electrumx_dir.exists():
            os.chdir(self.app_state.electrumx_dir)
            result = subprocess.run(
                f"git config --get remote.origin.url",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.stdout.strip() == url:
                print(f"- electrumx is already installed (url={url})")
                checkout_branch(branch)
                subprocess.run(f"git pull", shell=True, check=True)
                # Todo - cannot re-install requirements dynamically because of plyvel
                #  awaiting a PR for electrumx

            if result.stdout.strip() != url:
                existing_fork = self.app_state.electrumx_dir
                print(f"- alternate fork of electrumx is already installed")
                print(f"- moving existing fork (to '{existing_fork}.bak')")
                print(f"- installing electrumsv (url={url})")
                os.rename(
                    self.app_state.electrumx_dir,
                    self.app_state.electrumx_dir.with_suffix(".bak"),
                )
                self.app_state.install_tools.install_electrumx(url, branch)

    def local_electrumx(self, path, branch):
        self.app_state.install_tools.generate_run_script_electrumx()

    def node(self, branch):
        """this one has a pip installer at https://pypi.org/project/electrumsv-node/"""
        self.app_state.install_tools.install_bitcoin_node()

    def status_monitor(self):
        """purely for generating the .bat / .sh script"""
        self.app_state.install_tools.install_status_monitor()
