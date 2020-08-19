import logging
import subprocess
from pathlib import Path

from .components import ComponentName
from .installers import Installers

logger = logging.getLogger("install-handlers")


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
        self.app_state = app_state
        self.installer = Installers(self.app_state)
        self.controller = self.app_state.controller

    def validate_only_one_mode(self, parsed_args):
        modes_selected = []
        count_true = 0
        for cmd, mode in parsed_args.__dict__.items():
            if mode:
                modes_selected.append(cmd)
                count_true += 1
        if count_true not in [0, 1]:
            return False, modes_selected
        return True, modes_selected

    def handle_remote_repo(self, package_name, url, branch):
        print(f"- installing remote dependency for {package_name} at {url}")

        if package_name == ComponentName.ELECTRUMSV:
            self.installer.remote_electrumsv(url, branch)

        if package_name == ComponentName.ELECTRUMX:
            self.installer.remote_electrumx(url, branch)

        if package_name == ComponentName.NODE:
            self.installer.node(branch)

    def handle_local_repo(self, package_name, path, branch):
        try:
            print(f"- installing local dependency for {package_name} at path: {path}")
            assert Path(path).exists(), f"the path {path} to {package_name} does not exist!"
            if branch != "":
                subprocess.run(f"git checkout {branch}", shell=True, check=True)

            if package_name == ComponentName.ELECTRUMSV:
                self.installer.local_electrumsv(path, branch)

            if package_name == ComponentName.ELECTRUMX:
                self.installer.local_electrumx(path, branch)

        except Exception as e:
            raise e

    # ----- MAIN ARGUMENT HANDLERS ----- #
    def handle_top_level_args(self, parsed_args):
        if not self.app_state.NAMESPACE == self.app_state.TOP_LEVEL:
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
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        valid_input, modes_selected = self.validate_only_one_mode(parsed_args)
        if not valid_input:
            print(f"You must only select ONE mode of operation. You selected '{modes_selected}'")
            return

        if parsed_args.full_stack:
            self.app_state.start_set.add(ComponentName.ELECTRUMSV)
            self.app_state.start_set.add(ComponentName.ELECTRUMX)
            self.app_state.start_set.add(ComponentName.NODE)

        elif parsed_args.esv_ex_node:
            self.app_state.start_set.add(ComponentName.ELECTRUMSV)
            self.app_state.start_set.add(ComponentName.ELECTRUMX)
            self.app_state.start_set.add(ComponentName.NODE)

        elif parsed_args.esv_idx_node:
            raise NotImplementedError("esv_idx_node mode is not supported yet")

        elif parsed_args.ex_node:
            self.app_state.start_set.add(ComponentName.ELECTRUMX)
            self.app_state.start_set.add(ComponentName.NODE)

        elif parsed_args.node:
            self.app_state.start_set.add(ComponentName.NODE)

        else:  # no args defaults to '--full_stack'
            self.app_state.start_set.add(ComponentName.ELECTRUMSV)
            self.app_state.start_set.add(ComponentName.ELECTRUMX)
            self.app_state.start_set.add(ComponentName.NODE)

        if parsed_args.extapp_path != "":
            raise NotImplementedError(
                "loading extapps on the electrumsv daemon is " "not supported yet"
            )

    def handle_stop_args(self, parsed_args):
        """takes no arguments"""
        if not self.app_state.NAMESPACE == self.app_state.STOP:
            return

    def handle_reset_args(self, parsed_args):
        """takes no arguments"""
        if not self.app_state.NAMESPACE == self.app_state.RESET:
            return

    def handle_node_args(self, parsed_args):
        """parsed_args are actually raw args. feeds runners.node() via Config.node_args"""
        if not self.app_state.NAMESPACE == ComponentName.NODE:
            return
        self.app_state.node_args = parsed_args

    def handle_status_args(self, parsed_args):
        """takes no arguments"""
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        self.installer.status_monitor()

    def handle_electrumsv_args(self, parsed_args):
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.ELECTRUMSV in self.app_state.start_set:
            print()
            print(f"{ComponentName.ELECTRUMSV} not required")
            print(f"- skipping installation of {ComponentName.ELECTRUMSV}")
            return
        print()
        print(f"{ComponentName.ELECTRUMSV} is required")
        print(f"-------------------------------")

        # dapp_path
        if parsed_args.dapp_path != "":
            raise NotImplementedError("loading dapps on the electrumsv daemon is not supported yet")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/electrumsv/electrumsv.git"
            self.app_state.set_electrumsv_path(self.app_state.depends_dir.joinpath("electrumsv"))
            self.handle_remote_repo(ComponentName.ELECTRUMSV, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            self.app_state.set_electrumsv_path(self.app_state.depends_dir.joinpath("electrumsv"))
            self.handle_remote_repo(ComponentName.ELECTRUMSV, parsed_args.repo, parsed_args.branch)
        else:
            self.app_state.set_electrumsv_path(Path(parsed_args.repo))
            self.handle_local_repo(ComponentName.ELECTRUMSV, parsed_args.repo, parsed_args.branch)

    def handle_electrumx_args(self, parsed_args):
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.ELECTRUMX in self.app_state.start_set:
            print()
            print(f"{ComponentName.ELECTRUMX} not required")
            print(f"-------------------------------")
            print(f"- skipping installation of {ComponentName.NODE}")
            return

        print()
        print(f"{ComponentName.ELECTRUMX} is required")
        print(f"-------------------------------")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/kyuupichan/electrumx.git"
            self.handle_remote_repo(ComponentName.ELECTRUMX, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            self.handle_remote_repo(ComponentName.ELECTRUMX, parsed_args.repo, parsed_args.branch)
        else:
            self.handle_local_repo(ComponentName.ELECTRUMX, parsed_args.repo, parsed_args.branch)

    def handle_electrumsv_node_args(self, parsed_args):
        """not to be confused with node namespace:
        > electrumsv-sdk node <rpc commands>
        This is for the subcommand of the 'start' namespace:
        > 'electrumsv-sdk start electrumsv_node repo=<repo> branch=<branch>'
        """
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        # print("handle_electrumsv_node_args")
        if not ComponentName.NODE in self.app_state.start_set:
            print()
            print(f"{ComponentName.NODE} not required")
            print(f"- skipping installation of {ComponentName.NODE}")
            return
        print()
        print(f"{ComponentName.NODE} is required")
        print(f"-------------------------------")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "https://github.com/electrumsv/electrumsv_node.git"
            self.handle_remote_repo(ComponentName.NODE, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            self.handle_remote_repo(ComponentName.NODE, parsed_args.repo, parsed_args.branch)
        else:
            self.handle_local_repo(ComponentName.NODE, parsed_args.repo, parsed_args.branch)

    def handle_indexer_args(self, parsed_args):
        if not self.app_state.NAMESPACE == self.app_state.START:
            return

        if not ComponentName.INDEXER in self.app_state.start_set:
            print()
            print(f"{ComponentName.INDEXER} not required")
            print(f"-------------------------------")
            print(f"- skipping installation of {ComponentName.INDEXER}")
            return
        print()
        print(f"{ComponentName.INDEXER} is required")
        raise NotImplementedError("electrumsv_indexer installation is not supported yet.")

        if parsed_args.repo == "":  # default
            parsed_args.repo = "????"
            self.handle_remote_repo(ComponentName.INDEXER, parsed_args.repo, parsed_args.branch)
        elif parsed_args.repo.startswith("https://"):
            self.handle_remote_repo(ComponentName.INDEXER, parsed_args.repo, parsed_args.branch)
        else:
            self.handle_local_repo(ComponentName.INDEXER, parsed_args.repo, parsed_args.branch)

    # ----- HANDLERS ENTRY POINT ----- #

    def handle_install(self):
        for cmd, parsed_args in self.app_state.subcmd_parsed_args_map.items():
            func = getattr(self, "handle_" + cmd + "_args")
            func(parsed_args)
