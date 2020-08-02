import os
import subprocess
import sys

from electrumsv_sdk.utils import checkout_branch, create_if_not_exist


class Installers:
    def __init__(self, app_state):
        self.app_sate = app_state

    def remote_electrumsv(self, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        if not self.app_sate.electrumsv_dir.exists():
            print(f"- installing electrumsv (url={url})")
            self.app_sate.install_tools.install_electrumsv(url, branch)

        elif self.app_sate.electrumsv_dir.exists():
            os.chdir(self.app_sate.electrumsv_dir.__str__())
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
                    f"{self.app_sate.electrumsv_requirements_path}",
                    shell=True,
                    check=True,
                )
                subprocess.run(
                    f"{sys.executable} -m pip install -r "
                    f"{self.app_sate.electrumsv_binary_requirements_path}",
                    shell=True,
                    check=True,
                )
            if result.stdout.strip() != url:
                existing_fork = self.app_sate.electrumsv_dir.__str__()
                print(f"- alternate fork of electrumsv is already installed")
                print(f"- moving existing fork (to {existing_fork.__str__() + '.bak'}")
                print(f"- installing electrumsv (url={url})")
                os.rename(
                    self.app_sate.electrumsv_dir.__str__(),
                    self.app_sate.electrumsv_dir.__str__() + ".bak",
                )
                self.app_sate.install_tools.install_electrumsv(url, branch)

        create_if_not_exist(self.app_sate.electrumsv_regtest_wallets_dir)

    def local_electrumsv(self, url, branch):
        create_if_not_exist(self.app_sate.electrumsv_regtest_wallets_dir)
        self.app_sate.install_tools.generate_run_scripts_electrumsv()

    def remote_electrumx(self, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        if not self.app_sate.electrumx_dir.exists():
            print(f"- installing electrumx (url={url})")
            self.app_sate.install_tools.install_electrumx(url, branch)
        elif self.app_sate.electrumx_dir.exists():
            os.chdir(self.app_sate.electrumx_dir.__str__())
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
                existing_fork = self.app_sate.electrumx_dir.__str__()
                print(f"- alternate fork of electrumx is already installed")
                print(f"- moving existing fork (to {existing_fork.__str__() + '.bak'}")
                print(f"- installing electrumsv (url={url})")
                os.rename(
                    self.app_sate.electrumx_dir.__str__(),
                    self.app_sate.electrumx_dir.__str__() + ".bak",
                )
                self.app_sate.install_tools.install_electrumx(url, branch)

    def local_electrumx(self, path, branch):
        self.app_sate.install_tools.generate_run_script_electrumx()

    def node(self, branch):
        """this one has a pip installer at https://pypi.org/project/electrumsv-node/"""
        self.app_sate.install_tools.install_bitcoin_node()

    def status_monitor(self):
        """purely for generating the .bat / .sh script"""
        self.app_sate.install_tools.install_status_monitor()
