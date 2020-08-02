import logging
import os
import sys
import subprocess
from pathlib import Path

from .utils import checkout_branch, create_if_not_exist

logger = logging.getLogger("install-handlers")

def validate_only_one_mode(parsed_args):
    modes_selected = []
    count_true = 0
    for cmd, mode in parsed_args.__dict__.items():
        if mode:
            modes_selected.append(cmd)
            count_true += 1
    if count_true not in [0, 1]:
        return False, modes_selected
    return True, modes_selected


class Installers:

    def __init__(self, app_state):
        self.app_sate = app_state

    def check_remote_electrumsv_install(self, url, branch):
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
                    f"{sys.executable} -m pip install -r {self.app_sate.electrumsv_requirements_path}",
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

    def check_local_electrumsv_install(self, url, branch):
        create_if_not_exist(self.app_sate.electrumsv_regtest_wallets_dir)
        self.app_sate.install_tools.generate_run_scripts_electrumsv()

    def check_remote_electrumx_install(self, url, branch):
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

    def check_local_electrumx_install(self, path, branch):
        self.app_sate.install_tools.generate_run_script_electrumx()

    def check_node_install(self, branch):
        """this one has a pip installer at https://pypi.org/project/electrumsv-node/"""
        self.app_sate.install_tools.install_bitcoin_node()

    def check_status_monitor_install(self):
        """purely for generating the .bat / .sh script"""
        self.app_sate.install_tools.install_status_monitor()


class Handlers:
    """The handlers associated with the 'start' command check to see what is already installed
    compared to the cli inputs and if not installed and it is required will proceed to install
    the missing dependency.

    NOTE: if there is a conflict (e.g. installing a remote forked github repo would over-write
    the existing install of the official github repo) then a ".bak: backup will be created for
    the existing version of the repo.

    No arg ("") will default to the 'official' github repo.

    All handlers are called no matter what and args are fed to them - if any. But if their
    relevant namespace is not 'active' (i.e. 'start', 'stop' or 'reset') then they do not action
    anything -> return
    """
    def __init__(self, app_state: "AppState"):
        self.app_sate = app_state
        self.install_checker = Installers(self.app_sate)
        self.controller = self.app_sate.controller

    def handle_remote_repo(self, package_name, url, branch):
        print(f"- installing remote dependency for {package_name} at {url}")

        if package_name == self.app_sate.ELECTRUMSV:
            self.install_checker.check_remote_electrumsv_install(url, branch)

        if package_name == self.app_sate.ELECTRUMX:
            self.install_checker.check_remote_electrumx_install(url, branch)

        if package_name == self.app_sate.ELECTRUMSV_NODE:
            self.install_checker.check_node_install(branch)

    def handle_local_repo(self, package_name, path, branch):
        try:
            print(f"- installing local dependency for {package_name} at path: {path}")
            assert Path(path).exists(), f"the path {path} to {package_name} does not exist!"
            if branch != "":
                subprocess.run(f"git checkout {branch}", shell=True, check=True)

            if package_name == self.app_sate.ELECTRUMSV:
                self.install_checker.check_local_electrumsv_install(path, branch)

            if package_name == self.app_sate.ELECTRUMX:
                self.install_checker.check_local_electrumx_install(path, branch)

        except Exception as e:
            raise e

    # ----- MAIN ARGUMENT HANDLERS ----- #
    def handle_top_level_args(self, parsed_args):
        if not self.app_sate.NAMESPACE == self.app_sate.TOP_LEVEL:
            return

        # print("TOP LEVEL ARGS HANDLER")
        # print(f"parsed_args={parsed_args}")

    def handle_start_args(self, parsed_args):
        """the top-level arguments (preceeding any subcommand) cover two main functionalities:
        1) mode of operation:
        --full-stack OR --node OR --ex-node OR --esv-ex-node OR --esv-idx-node
        2) extension 3rd party applications launched against the rest of the stack:
        --extapp EXTAPP_PATH1 --extapp EXTAPP_PATH2 --extapp EXTAPP_PATH3 ...

        For (1), a set of required dependencies is gathered and is then satisfied
        by the handlers below for the given dependency.
        For (2), extension app support is not supported yet (but will allow for any non-python
        servers to be run (e.g. a localhost blockexplorer perhaps)
        """
        if not self.app_sate.NAMESPACE == self.app_sate.START:
            return

        valid_input, modes_selected = validate_only_one_mode(parsed_args)
        if not valid_input:
            print(f"You must only select ONE mode of operation. You selected '{modes_selected}'")
            return

        if parsed_args.full_stack:
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMSV)
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMX)
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMSV_NODE)

        elif parsed_args.esv_ex_node:
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMSV)
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMX)
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMSV_NODE)

        elif parsed_args.esv_idx_node:
            raise NotImplementedError("esv_idx_node mode is not supported yet")

        elif parsed_args.ex_node:
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMX)
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMSV_NODE)

        elif parsed_args.node:
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMSV_NODE)

        else:  # no args defaults to '--full_stack'
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMSV)
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMX)
            self.app_sate.required_dependencies_set.add(self.app_sate.ELECTRUMSV_NODE)

        if parsed_args.extapp_path != "":
            raise NotImplementedError(
                "loading extapps on the electrumsv daemon is " "not supported yet"
            )

    def handle_stop_args(self, parsed_args):
        """takes no arguments"""
        if not self.app_sate.NAMESPACE == self.app_sate.STOP:
            return

        # self.controller.stop()

    def handle_reset_args(self, parsed_args):
        """takes no arguments"""
        if not self.app_sate.NAMESPACE == self.app_sate.RESET:
            return

    def handle_node_args(self, parsed_args):
        """parsed_args are actually raw args. feeds runners.node() via Config.node_args"""
        if not self.app_sate.NAMESPACE == self.app_sate.NODE:
            return
        self.app_sate.node_args = parsed_args

    def handle_status_args(self, parsed_args):
        """takes no arguments"""
        if not self.app_sate.NAMESPACE == self.app_sate.START:
            return

        self.install_checker.check_status_monitor_install()

    def handle_electrumsv_args(self, parsed_args):
        if not self.app_sate.NAMESPACE == self.app_sate.START:
            return

        if not self.app_sate.ELECTRUMSV in self.app_sate.required_dependencies_set:
            print()
            print(f"{self.app_sate.ELECTRUMSV} not required")
            print(f"- skipping installation of {self.app_sate.ELECTRUMSV}")
            return
        print()
        print(f"{self.app_sate.ELECTRUMSV} is required")
        print(f"-------------------------------")

        # dapp_path
        if parsed_args.dapp_path != "":
            raise NotImplementedError("loading dapps on the electrumsv daemon is not supported yet")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/electrumsv/electrumsv.git"
            self.app_sate.set_electrumsv_path(self.app_sate.depends_dir.joinpath("electrumsv"))
            self.handle_remote_repo(self.app_sate.ELECTRUMSV, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            self.app_sate.set_electrumsv_path(self.app_sate.depends_dir.joinpath("electrumsv"))
            self.handle_remote_repo(self.app_sate.ELECTRUMSV, parsed_args.repo, parsed_args.branch)
        else:
            self.app_sate.set_electrumsv_path(Path(parsed_args.repo))
            self.handle_local_repo(self.app_sate.ELECTRUMSV, parsed_args.repo, parsed_args.branch)

    def handle_electrumx_args(self, parsed_args):
        if not self.app_sate.NAMESPACE == self.app_sate.START:
            return

        if not self.app_sate.ELECTRUMX in self.app_sate.required_dependencies_set:
            print()
            print(f"{self.app_sate.ELECTRUMX} not required")
            print(f"-------------------------------")
            print(f"- skipping installation of {self.app_sate.ELECTRUMSV_NODE}")
            return

        print()
        print(f"{self.app_sate.ELECTRUMX} is required")
        print(f"-------------------------------")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/kyuupichan/electrumx.git"
            self.handle_remote_repo(self.app_sate.ELECTRUMX, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            self.handle_remote_repo(self.app_sate.ELECTRUMX, parsed_args.repo, parsed_args.branch)
        else:
            self.handle_local_repo(self.app_sate.ELECTRUMX, parsed_args.repo, parsed_args.branch)

    def handle_electrumsv_node_args(self, parsed_args):
        """not to be confused with node namespace:
        > electrumsv-sdk node <rpc commands>
        This is for the subcommand of the 'start' namespace:
        > 'electrumsv-sdk start electrumsv_node repo=<repo> branch=<branch>'
        """
        if not self.app_sate.NAMESPACE == self.app_sate.START:
            return

        # print("handle_electrumsv_node_args")
        if not self.app_sate.ELECTRUMSV_NODE in self.app_sate.required_dependencies_set:
            print()
            print(f"{self.app_sate.ELECTRUMSV_NODE} not required")
            print(f"- skipping installation of {self.app_sate.ELECTRUMSV_NODE}")
            return
        print()
        print(f"{self.app_sate.ELECTRUMSV_NODE} is required")
        print(f"-------------------------------")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/electrumsv/electrumsv_node.git"
            self.handle_remote_repo(self.app_sate.ELECTRUMSV_NODE, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            self.handle_remote_repo(self.app_sate.ELECTRUMSV_NODE, parsed_args.repo, parsed_args.branch)
        else:
            self.handle_local_repo(self.app_sate.ELECTRUMSV_NODE, parsed_args.repo, parsed_args.branch)

    def handle_indexer_args(self, parsed_args):
        if not self.app_sate.NAMESPACE == self.app_sate.START:
            return

        # print("handle_electrumsv_indexer_args")
        if not self.app_sate.ELECTRUMSV_INDEXER in self.app_sate.required_dependencies_set:
            print()
            print(f"{self.app_sate.ELECTRUMSV_INDEXER} not required")
            print(f"-------------------------------")
            print(f"- skipping installation of {self.app_sate.ELECTRUMSV_INDEXER}")
            return
        print()
        print(f"{self.app_sate.ELECTRUMSV_INDEXER} is required")
        raise NotImplementedError("electrumsv_indexer installation is not supported yet.")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "????"
            self.handle_remote_repo(self.app_sate.ELECTRUMSV_INDEXER, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            self.handle_remote_repo(self.app_sate.ELECTRUMSV_INDEXER, parsed_args.repo, parsed_args.branch)
        else:
            self.handle_local_repo(self.app_sate.ELECTRUMSV_INDEXER, parsed_args.repo, parsed_args.branch)


    # ----- HANDLERS ENTRY POINT ----- #

    def handle_install(self):
        for cmd, parsed_args in self.app_sate.subcmd_parsed_args_map.items():
            func = getattr(self, "handle_" + cmd + "_args")
            func(parsed_args)
