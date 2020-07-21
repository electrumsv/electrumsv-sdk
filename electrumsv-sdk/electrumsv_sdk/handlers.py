import os
import sys
import subprocess
from pathlib import Path

from .config import Config
from .install_tools import install_electrumsv, install_electrumsv_node, install_electrumx, \
    create_if_not_exist, generate_run_scripts_electrumsv, generate_run_script_electrumx
from .utils import checkout_branch


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
        if not Config.electrumsv_dir.exists():
            print(f"- installing electrumsv (url={url})")
            install_electrumsv(url, branch)

        elif Config.electrumsv_dir.exists():
            os.chdir(Config.electrumsv_dir.__str__())
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
                    f"{sys.executable} -m pip install -r {Config.electrumsv_requirements_path}",
                    shell=True,
                    check=True,
                )
                subprocess.run(
                    f"{sys.executable} -m pip install -r "
                    f"{Config.electrumsv_binary_requirements_path}",
                    shell=True,
                    check=True,
                )
            if result.stdout.strip() != url:
                existing_fork = Config.electrumsv_dir.__str__()
                print(f"- alternate fork of electrumsv is already installed")
                print(f"- moving existing fork (to {existing_fork.__str__() + '.bak'}")
                print(f"- installing electrumsv (url={url})")
                os.rename(
                    Config.electrumsv_dir.__str__(),
                    Config.electrumsv_dir.__str__() + ".bak",
                )
                install_electrumsv(url, branch)

        create_if_not_exist(Config.electrumsv_regtest_wallets_dir)

    @classmethod
    def check_local_electrumsv_install(cls, url, branch):
        generate_run_scripts_electrumsv()

    @classmethod
    def check_remote_electrumx_install(cls, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        if not Config.electrumx_dir.exists():
            print(f"- installing electrumx (url={url})")
            install_electrumx(url, branch)
        elif Config.electrumsv_dir.exists():
            os.chdir(Config.electrumx_dir.__str__())
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
                existing_fork = Config.electrumx_dir.__str__()
                print(f"- alternate fork of electrumx is already installed")
                print(f"- moving existing fork (to {existing_fork.__str__() + '.bak'}")
                print(f"- installing electrumsv (url={url})")
                os.rename(
                    Config.electrumsv_dir.__str__(),
                    Config.electrumsv_dir.__str__() + ".bak",
                )
                install_electrumsv(url, branch)

    @classmethod
    def check_local_electrumx_install(cls, path, branch):
        generate_run_script_electrumx()

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

            if package_name == Config.ELECTRUMSV:
                CheckInstall.check_local_electrumsv_install(path, branch)

            if package_name == Config.ELECTRUMX:
                CheckInstall.check_local_electrumx_install(path, branch)

        except Exception as e:
            raise e

    # ----- MAIN ARGUMENT HANDLERS ----- #
    @classmethod
    def handle_top_level_args(cls, parsed_args):
        if not Config.NAMESPACE == Config.TOP_LEVEL:
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
        if not Config.NAMESPACE == Config.START:
            return

        valid_input, modes_selected = validate_only_one_mode(parsed_args)
        if not valid_input:
            print(f"You must only select ONE mode of operation. You selected '{modes_selected}'")
            return

        if parsed_args.full_stack:
            Config.required_dependencies_set.add(Config.ELECTRUMSV)
            Config.required_dependencies_set.add(Config.ELECTRUMX)
            Config.required_dependencies_set.add(Config.ELECTRUMSV_NODE)

        elif parsed_args.esv_ex_node:
            Config.required_dependencies_set.add(Config.ELECTRUMSV)
            Config.required_dependencies_set.add(Config.ELECTRUMX)
            Config.required_dependencies_set.add(Config.ELECTRUMSV_NODE)

        elif parsed_args.esv_idx_node:
            raise NotImplementedError("esv_idx_node mode is not supported yet")

        elif parsed_args.ex_node:
            Config.required_dependencies_set.add(Config.ELECTRUMX)
            Config.required_dependencies_set.add(Config.ELECTRUMSV_NODE)

        elif parsed_args.node:
            Config.required_dependencies_set.add(Config.ELECTRUMSV_NODE)

        else:  # no args defaults to '--full_stack'
            Config.required_dependencies_set.add(Config.ELECTRUMSV)
            Config.required_dependencies_set.add(Config.ELECTRUMX)
            Config.required_dependencies_set.add(Config.ELECTRUMSV_NODE)

        if parsed_args.extapp_path != "":
            raise NotImplementedError(
                "loading extapps on the electrumsv daemon is " "not supported yet"
            )

    @classmethod
    def handle_stop_args(cls, parsed_args):
        """takes no arguments"""
        if not Config.NAMESPACE == Config.STOP:
            return

        # print("STOP ARGS HANDLER")
        # print(f"parsed_args={parsed_args}")

    @classmethod
    def handle_reset_args(cls, parsed_args):
        """takes no arguments"""
        if not Config.NAMESPACE == Config.RESET:
            return

        # print("RESET ARGS HANDLER")
        # print(f"parsed_args={parsed_args}")

    @classmethod
    def handle_electrumsv_args(cls, parsed_args):
        if not Config.NAMESPACE == Config.START:
            return

        if not Config.ELECTRUMSV in Config.required_dependencies_set:
            print()
            print(f"{Config.ELECTRUMSV} not required")
            print(f"- skipping installation of {Config.ELECTRUMSV}")
            return
        print()
        print(f"{Config.ELECTRUMSV} is required")
        print(f"-------------------------------")

        # dapp_path
        if parsed_args.dapp_path != "":
            raise NotImplementedError("loading dapps on the electrumsv daemon is not supported yet")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/electrumsv/electrumsv.git"
            Config.set_electrumsv_path(Config.depends_dir.joinpath("electrumsv"))
            cls.handle_remote_repo(Config.ELECTRUMSV, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            Config.set_electrumsv_path(Config.depends_dir.joinpath("electrumsv"))
            cls.handle_remote_repo(Config.ELECTRUMSV, parsed_args.repo, parsed_args.branch)
        else:
            Config.set_electrumsv_path(Path(parsed_args.repo))
            cls.handle_local_repo(Config.ELECTRUMSV, parsed_args.repo, parsed_args.branch)

    @classmethod
    def handle_electrumx_args(cls, parsed_args):
        if not Config.NAMESPACE == Config.START:
            return

        if not Config.ELECTRUMX in Config.required_dependencies_set:
            print()
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
        if not Config.NAMESPACE == Config.START:
            return

        # print("handle_electrumsv_node_args")
        if not Config.ELECTRUMSV_NODE in Config.required_dependencies_set:
            print()
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
        if not Config.NAMESPACE == Config.START:
            return

        # print("handle_electrumsv_indexer_args")
        if not Config.ELECTRUMSV_INDEXER in Config.required_dependencies_set:
            print()
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


def handle():
    for cmd, parsed_args in Config.subcmd_parsed_args_map.items():
        func = getattr(Handlers, "handle_" + cmd + "_args")
        func(parsed_args)
