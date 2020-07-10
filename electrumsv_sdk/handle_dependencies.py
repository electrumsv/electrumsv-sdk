import os
import sys
import subprocess
from pathlib import Path

from electrumsv_sdk.config import Config
from electrumsv_sdk.install_tools import install_electrumsv, install_electrumsv_node
from electrumsv_sdk.runners import run_electrumsv_daemon
from electrumsv_sdk.utils import checkout_branch


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
        if not Config.depends_dir_electrumsv.exists():
            print(f"- installing electrumsv (url={url})")
            install_electrumsv(url, branch)
        elif Config.depends_dir_electrumsv.exists():
            os.chdir(Config.depends_dir_electrumsv.__str__())
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
                    f"{sys.executable} -m pip install -r {Config.depends_dir_electrumsv_req}",
                    shell=True,
                    check=True,
                )
                subprocess.run(
                    f"{sys.executable} -m pip install -r "
                    f"{Config.depends_dir_electrumsv_req_bin}",
                    shell=True,
                    check=True,
                )
            if result.stdout.strip() != url:
                existing_fork = Config.depends_dir_electrumsv.__str__()
                print(f"- alternate fork of electrumsv is already installed")
                print(f"- moving existing fork (to {existing_fork.__str__() + '.bak'}")
                print(f"- installing electrumsv (url={url})")
                os.rename(
                    Config.depends_dir_electrumsv.__str__(),
                    Config.depends_dir_electrumsv.__str__() + ".bak",
                )
                install_electrumsv(url, branch)

    @classmethod
    def check_remote_electrumx_install(cls, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match)
        """
        if not Config.depends_dir_electrumx.exists():
            print("- installing electrumx")
            # install_electrumx()
        elif Config.depends_dir_electrumsv.exists():
            os.chdir(Config.depends_dir_electrumx.__str__())
            result = subprocess.run(f"git config --get remote.origin.url", shell=True, check=True)
            if result.stdout == url:
                # attempt pull and reinstall dependencies that may have changed.
                print(f"url for electrumx = {result.stdout}")
            if result.stdout != url:
                print(f"url for electrumx = {result.stdout}")
                # todo - rename to electrumx.bak to
                #  and only then do install_electrumsv

    @classmethod
    def check_remote_electrumsv_node_install(cls, branch):
        """this one has a pip installer at https://pypi.org/project/electrumsv-node/"""
        install_electrumsv_node()


class Handlers:
    """handlers check to see what is already installed compared to the cli inputs and
    if not installed and it is required will proceed to install the missing dependency.

    NOTE: if there is a conflict (e.g. installing a remote forked github repo would over-write
    the existing install of the official github repo) then a ".bak: backup will be created for
    the existing version of the repo (just in case the user was using that repo for local
    development
    - would hate to destroy all of their hard work!

    No arg ("") will default to the 'official' github repo.
    """

    @classmethod
    def handle_remote_repo(cls, package_name, url, branch):
        print(f"- installing remote dependency for {package_name} at {url}")

        if package_name == Config.ELECTRUMSV:
            CheckInstall.check_remote_electrumsv_install(url, branch)

        if package_name == Config.ELECTRUMX:
            CheckInstall.check_remote_electrumx_install(url, branch)

        if package_name == Config.ELECTRUMSV_NODE:
            CheckInstall.check_remote_electrumsv_node_install(branch)

    @classmethod
    def handle_local_repo(cls, package_name, path, branch):
        try:
            print(f"- installing local dependency for {package_name} at path: {path}")
            assert Path(path).exists(), f"the path {path} to {package_name} does not exist!"
            if branch != "":
                subprocess.run(f"git checkout {branch}", shell=True, check=True)
        except Exception as e:
            raise e

    # ----- MAIN ARGUMENT HANDLERS ----- #

    @classmethod
    def handle_electrumsv_sdk_args(cls, parsed_args):
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
        valid_input, modes_selected = validate_only_one_mode(parsed_args)
        if not valid_input:
            print(f"You must only select ONE mode of operation. You selected '{modes_selected}'")
            return

        if parsed_args.full_stack:
            Config.required_dependencies_set.add(Config.ELECTRUMSV)
            Config.required_dependencies_set.add(Config.ELECTRUMX)
            Config.required_dependencies_set.add(Config.ELECTRUMSV_NODE)

        if parsed_args.esv_ex_node:
            Config.required_dependencies_set.add(Config.ELECTRUMSV)
            Config.required_dependencies_set.add(Config.ELECTRUMX)
            Config.required_dependencies_set.add(Config.ELECTRUMSV_NODE)

        if parsed_args.esv_idx_node:
            raise NotImplementedError("esv_idx_node mode is not supported yet")

        if parsed_args.ex_node:
            Config.required_dependencies_set.add(Config.ELECTRUMX)
            Config.required_dependencies_set.add(Config.ELECTRUMSV_NODE)

        if parsed_args.node:
            raise NotImplementedError("node mode is not supported yet")

        if parsed_args.extapp_path != "":
            raise NotImplementedError(
                "loading extapps on the electrumsv daemon is " "not supported yet"
            )
        else:  # no args defaults to '--full_stack'
            Config.required_dependencies_set.add(Config.ELECTRUMSV)
            Config.required_dependencies_set.add(Config.ELECTRUMX)
            Config.required_dependencies_set.add(Config.ELECTRUMSV_NODE)

    @classmethod
    def handle_electrumsv_args(cls, parsed_args):
        if not Config.ELECTRUMSV in Config.required_dependencies_set:
            print(f"{Config.ELECTRUMSV} not required")
            print(f"- skipping installation of {Config.ELECTRUMSV_NODE}")
            return
        print(f"{Config.ELECTRUMSV} is required")
        print(f"-------------------------------")

        # dapp_path
        if parsed_args.dapp_path != "":
            raise NotImplementedError("loading dapps on the electrumsv daemon is not supported yet")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/electrumsv/electrumsv.git"
            cls.handle_remote_repo(Config.ELECTRUMSV, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            cls.handle_remote_repo(Config.ELECTRUMSV, parsed_args.repo, parsed_args.branch)
        else:
            cls.handle_local_repo(Config.ELECTRUMSV, parsed_args.repo, parsed_args.branch)

    @classmethod
    def handle_electrumx_args(cls, parsed_args):
        if not Config.ELECTRUMX in Config.required_dependencies_set:
            print(f"{Config.ELECTRUMX} not required")
            print(f"-------------------------------")
            print(f"- skipping installation of {Config.ELECTRUMSV_NODE}")
            return

        print()
        print(f"{Config.ELECTRUMX} is required")
        print(f"-------------------------------")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/kyuupichan/electrumx.git"
            cls.handle_remote_repo(Config.ELECTRUMX, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            cls.handle_remote_repo(Config.ELECTRUMX, parsed_args.repo, parsed_args.branch)
        else:
            cls.handle_local_repo(Config.ELECTRUMX, parsed_args.repo, parsed_args.branch)

    @classmethod
    def handle_electrumsv_node_args(cls, parsed_args):
        # print("handle_electrumsv_node_args")
        if not Config.ELECTRUMSV_NODE in Config.required_dependencies_set:
            print(f"{Config.ELECTRUMSV_NODE} not required")
            print(f"- skipping installation of {Config.ELECTRUMSV_NODE}")
            return
        print()
        print(f"{Config.ELECTRUMSV_NODE} is required")
        print(f"-------------------------------")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/electrumsv/electrumsv_node.git"
            cls.handle_remote_repo(Config.ELECTRUMSV_NODE, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            cls.handle_remote_repo(Config.ELECTRUMSV_NODE, parsed_args.repo, parsed_args.branch)
        else:
            cls.handle_local_repo(Config.ELECTRUMSV_NODE, parsed_args.repo, parsed_args.branch)

    @classmethod
    def handle_electrumsv_indexer_args(cls, parsed_args):
        # print("handle_electrumsv_indexer_args")
        if not Config.ELECTRUMSV_INDEXER in Config.required_dependencies_set:
            print(f"{Config.ELECTRUMSV_INDEXER} not required")
            print(f"-------------------------------")
            print(f"- skipping installation of {Config.ELECTRUMSV_INDEXER}")
            return
        print()
        print(f"{Config.ELECTRUMSV_INDEXER} is required")
        raise NotImplementedError("electrumsv_indexer installation is not supported yet.")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "????"
            cls.handle_remote_repo(Config.ELECTRUMSV_INDEXER, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            cls.handle_remote_repo(Config.ELECTRUMSV_INDEXER, parsed_args.repo, parsed_args.branch)
        else:
            cls.handle_local_repo(Config.ELECTRUMSV_INDEXER, parsed_args.repo, parsed_args.branch)


# ----- HANDLERS ENTRY POINT ----- #


def handle_dependencies():
    for cmd, parsed_args in Config.subcmd_parsed_args_map.items():
        func = getattr(Handlers, "handle_" + cmd + "_args")
        func(parsed_args)
