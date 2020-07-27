import os
import sys
import subprocess
from pathlib import Path

from .app_state import AppState
from .install_tools import install_electrumsv, install_electrumsv_node, install_electrumx, \
    create_if_not_exist, generate_run_scripts_electrumsv, generate_run_script_electrumx
from .utils import checkout_branch
from .component_state import ComponentName



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


class CheckInstall:

    @classmethod
    def check_remote_electrumsv_install(cls, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        if not AppState.electrumsv_dir.exists():
            print(f"- installing electrumsv (url={url})")
            install_electrumsv(url, branch)

        elif AppState.electrumsv_dir.exists():
            os.chdir(AppState.electrumsv_dir.__str__())
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
                    f"{sys.executable} -m pip install -r {AppState.electrumsv_requirements_path}",
                    shell=True,
                    check=True,
                )
                subprocess.run(
                    f"{sys.executable} -m pip install -r "
                    f"{AppState.electrumsv_binary_requirements_path}",
                    shell=True,
                    check=True,
                )
            if result.stdout.strip() != url:
                existing_fork = AppState.electrumsv_dir.__str__()
                print(f"- alternate fork of electrumsv is already installed")
                print(f"- moving existing fork (to {existing_fork.__str__() + '.bak'}")
                print(f"- installing electrumsv (url={url})")
                os.rename(
                    AppState.electrumsv_dir.__str__(),
                    AppState.electrumsv_dir.__str__() + ".bak",
                )
                install_electrumsv(url, branch)

        create_if_not_exist(AppState.electrumsv_regtest_wallets_dir)

    @classmethod
    def check_local_electrumsv_install(cls, url, branch):
        create_if_not_exist(AppState.electrumsv_regtest_wallets_dir)
        generate_run_scripts_electrumsv()

    @classmethod
    def check_remote_electrumx_install(cls, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        if not AppState.electrumx_dir.exists():
            print(f"- installing electrumx (url={url})")
            install_electrumx(url, branch)
        elif AppState.electrumx_dir.exists():
            os.chdir(AppState.electrumx_dir.__str__())
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
                existing_fork = AppState.electrumx_dir.__str__()
                print(f"- alternate fork of electrumx is already installed")
                print(f"- moving existing fork (to {existing_fork.__str__() + '.bak'}")
                print(f"- installing electrumsv (url={url})")
                os.rename(
                    AppState.electrumx_dir.__str__(),
                    AppState.electrumx_dir.__str__() + ".bak",
                )
                install_electrumx(url, branch)

    @classmethod
    def check_local_electrumx_install(cls, path, branch):
        generate_run_script_electrumx()

    @classmethod
    def check_remote_electrumsv_node_install(cls, branch):
        """this one has a pip installer at https://pypi.org/project/electrumsv-node/"""
        install_electrumsv_node()


class InstallHandlers:
    """handlers check to see what is already installed compared to the cli inputs and
    if not installed and it is required will proceed to install the missing dependency.

    NOTE: if there is a conflict (e.g. installing a remote forked github repo would over-write
    the existing install of the official github repo) then a ".bak: backup will be created for
    the existing version of the repo (just in case the user was using that repo for local
    development
    - would hate to destroy all of their hard work!

    No arg ("") will default to the 'official' github repo.

    All handlers are called no matter what and args are fed to them - if any. But if their
    relevant namespace is not 'active' (i.e. 'start', 'stop' or 'reset') then they do not action
    anything -> return
    """

    @classmethod
    def handle_remote_repo(cls, package_name, url, branch):
        print(f"- installing remote dependency for {package_name} at {url}")

        if package_name == AppState.ELECTRUMSV:
            CheckInstall.check_remote_electrumsv_install(url, branch)

        if package_name == AppState.ELECTRUMX:
            CheckInstall.check_remote_electrumx_install(url, branch)

        if package_name == AppState.ELECTRUMSV_NODE:
            CheckInstall.check_remote_electrumsv_node_install(branch)

    @classmethod
    def handle_local_repo(cls, package_name, path, branch):
        try:
            print(f"- installing local dependency for {package_name} at path: {path}")
            assert Path(path).exists(), f"the path {path} to {package_name} does not exist!"
            if branch != "":
                subprocess.run(f"git checkout {branch}", shell=True, check=True)

            if package_name == AppState.ELECTRUMSV:
                CheckInstall.check_local_electrumsv_install(path, branch)

            if package_name == AppState.ELECTRUMX:
                CheckInstall.check_local_electrumx_install(path, branch)

        except Exception as e:
            raise e

    # ----- MAIN ARGUMENT HANDLERS ----- #
    @classmethod
    def handle_top_level_args(cls, parsed_args):
        if not AppState.NAMESPACE == AppState.TOP_LEVEL:
            return

        # print("TOP LEVEL ARGS HANDLER")
        # print(f"parsed_args={parsed_args}")

    @classmethod
    def handle_start_args(cls, parsed_args):
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
        if not AppState.NAMESPACE == AppState.START:
            return

        valid_input, modes_selected = validate_only_one_mode(parsed_args)
        if not valid_input:
            print(f"You must only select ONE mode of operation. You selected '{modes_selected}'")
            return

        if parsed_args.full_stack:
            AppState.required_dependencies_set.add(AppState.ELECTRUMSV)
            AppState.required_dependencies_set.add(AppState.ELECTRUMX)
            AppState.required_dependencies_set.add(AppState.ELECTRUMSV_NODE)

        elif parsed_args.esv_ex_node:
            AppState.required_dependencies_set.add(AppState.ELECTRUMSV)
            AppState.required_dependencies_set.add(AppState.ELECTRUMX)
            AppState.required_dependencies_set.add(AppState.ELECTRUMSV_NODE)

        elif parsed_args.esv_idx_node:
            raise NotImplementedError("esv_idx_node mode is not supported yet")

        elif parsed_args.ex_node:
            AppState.required_dependencies_set.add(AppState.ELECTRUMX)
            AppState.required_dependencies_set.add(AppState.ELECTRUMSV_NODE)

        elif parsed_args.node:
            AppState.required_dependencies_set.add(AppState.ELECTRUMSV_NODE)

        else:  # no args defaults to '--full_stack'
            AppState.required_dependencies_set.add(AppState.ELECTRUMSV)
            AppState.required_dependencies_set.add(AppState.ELECTRUMX)
            AppState.required_dependencies_set.add(AppState.ELECTRUMSV_NODE)

        if parsed_args.extapp_path != "":
            raise NotImplementedError(
                "loading extapps on the electrumsv daemon is " "not supported yet"
            )

    @classmethod
    def handle_stop_args(cls, parsed_args):
        """takes no arguments"""
        if not AppState.NAMESPACE == AppState.STOP:
            return

    @classmethod
    def handle_reset_args(cls, parsed_args):
        """takes no arguments"""
        if not AppState.NAMESPACE == AppState.RESET:
            return

    @classmethod
    def handle_node_args(cls, parsed_args):
        """parsed_args are actually raw args. feeds runners.node() via Config.node_args"""
        if not AppState.NAMESPACE == AppState.NODE:
            return
        AppState.node_args = parsed_args

    @classmethod
    def handle_status_args(cls, parsed_args):
        """takes no arguments"""
        if not AppState.NAMESPACE == AppState.STATUS:
            return

    @classmethod
    def handle_electrumsv_args(cls, parsed_args):
        if not AppState.NAMESPACE == AppState.START:
            return

        if not AppState.ELECTRUMSV in AppState.required_dependencies_set:
            print()
            print(f"{AppState.ELECTRUMSV} not required")
            print(f"- skipping installation of {AppState.ELECTRUMSV}")
            return
        print()
        print(f"{AppState.ELECTRUMSV} is required")
        print(f"-------------------------------")

        # dapp_path
        if parsed_args.dapp_path != "":
            raise NotImplementedError("loading dapps on the electrumsv daemon is not supported yet")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/electrumsv/electrumsv.git"
            AppState.set_electrumsv_path(AppState.depends_dir.joinpath("electrumsv"))
            cls.handle_remote_repo(AppState.ELECTRUMSV, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            AppState.set_electrumsv_path(AppState.depends_dir.joinpath("electrumsv"))
            cls.handle_remote_repo(AppState.ELECTRUMSV, parsed_args.repo, parsed_args.branch)
        else:
            AppState.set_electrumsv_path(Path(parsed_args.repo))
            cls.handle_local_repo(AppState.ELECTRUMSV, parsed_args.repo, parsed_args.branch)

    @classmethod
    def handle_electrumx_args(cls, parsed_args):
        if not AppState.NAMESPACE == AppState.START:
            return

        if not AppState.ELECTRUMX in AppState.required_dependencies_set:
            print()
            print(f"{AppState.ELECTRUMX} not required")
            print(f"-------------------------------")
            print(f"- skipping installation of {AppState.ELECTRUMSV_NODE}")
            return

        print()
        print(f"{AppState.ELECTRUMX} is required")
        print(f"-------------------------------")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/kyuupichan/electrumx.git"
            cls.handle_remote_repo(AppState.ELECTRUMX, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            cls.handle_remote_repo(AppState.ELECTRUMX, parsed_args.repo, parsed_args.branch)
        else:
            cls.handle_local_repo(AppState.ELECTRUMX, parsed_args.repo, parsed_args.branch)

    @classmethod
    def handle_electrumsv_node_args(cls, parsed_args):
        """not to be confused with node namespace:
        > electrumsv-sdk node <rpc commands>
        This is for the subcommand of the 'start' namespace:
        > 'electrumsv-sdk start electrumsv_node repo=<repo> branch=<branch>'
        """
        if not AppState.NAMESPACE == AppState.START:
            return

        # print("handle_electrumsv_node_args")
        if not AppState.ELECTRUMSV_NODE in AppState.required_dependencies_set:
            print()
            print(f"{AppState.ELECTRUMSV_NODE} not required")
            print(f"- skipping installation of {AppState.ELECTRUMSV_NODE}")
            return
        print()
        print(f"{AppState.ELECTRUMSV_NODE} is required")
        print(f"-------------------------------")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/electrumsv/electrumsv_node.git"
            cls.handle_remote_repo(AppState.ELECTRUMSV_NODE, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            cls.handle_remote_repo(AppState.ELECTRUMSV_NODE, parsed_args.repo, parsed_args.branch)
        else:
            cls.handle_local_repo(AppState.ELECTRUMSV_NODE, parsed_args.repo, parsed_args.branch)

    @classmethod
    def handle_indexer_args(cls, parsed_args):
        if not AppState.NAMESPACE == AppState.START:
            return

        # print("handle_electrumsv_indexer_args")
        if not AppState.ELECTRUMSV_INDEXER in AppState.required_dependencies_set:
            print()
            print(f"{AppState.ELECTRUMSV_INDEXER} not required")
            print(f"-------------------------------")
            print(f"- skipping installation of {AppState.ELECTRUMSV_INDEXER}")
            return
        print()
        print(f"{AppState.ELECTRUMSV_INDEXER} is required")
        raise NotImplementedError("electrumsv_indexer installation is not supported yet.")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "????"
            cls.handle_remote_repo(AppState.ELECTRUMSV_INDEXER, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            cls.handle_remote_repo(AppState.ELECTRUMSV_INDEXER, parsed_args.repo, parsed_args.branch)
        else:
            cls.handle_local_repo(AppState.ELECTRUMSV_INDEXER, parsed_args.repo, parsed_args.branch)


# ----- HANDLERS ENTRY POINT ----- #


def handle_install():
    for cmd, parsed_args in AppState.subcmd_parsed_args_map.items():
        func = getattr(InstallHandlers, "handle_" + cmd + "_args")
        func(parsed_args)
