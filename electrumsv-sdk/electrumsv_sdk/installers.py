import logging
import os
import subprocess
import sys
import socket
import errno
from pathlib import Path


from .constants import DEFAULT_ID_ELECTRUMSV, DEFAULT_PORT_ELECTRUMSV
from .components import ComponentOptions, ComponentName
from .utils import checkout_branch, make_shell_script_for_component, make_esv_gui_script, \
    make_esv_daemon_script, make_esv_custom_script

logger = logging.getLogger("installers")


class Installers:
    def __init__(self, app_state):
        self.app_state = app_state

    def is_new_and_no_id(self, id, new) -> bool:
        return id == "" and new

    def is_new_and_id(self, id, new) -> bool:
        return id != "" and new

    def is_not_new_and_no_id(self, id, new) -> bool:
        return id == "" and not new

    def is_not_new_and_id(self, id, new) -> bool:
        return id != "" and not new

    def get_component_data_dir_for_id(self, component_name: ComponentName, component_data_dir:
            Path, id=None):
        """to run multiple instances of electrumsv requires multiple data directories (with
        separate lock files)"""
        new = self.app_state.start_options[ComponentOptions.NEW]
        if not id:
            id = self.app_state.start_options[ComponentOptions.ID]

        # autoincrement (electrumsv1 -> electrumsv2 -> electrumsv3...)
        if self.is_new_and_no_id(id, new):
            count = 1
            while True:
                self.app_state.start_options[ComponentOptions.ID] = id = \
                    str(component_name) + str(count)
                new_dir = component_data_dir.joinpath(id)
                if not new_dir.exists():
                    break
                else:
                    count += 1
            logger.debug(f"Using new user-specified electrumsv data dir ({id})")

        elif self.is_new_and_id(id, new):
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            if new_dir.exists():
                logger.debug(f"User-specified electrumsv data directory: {new_dir} already exists ("
                      f"either drop the --new flag or choose a unique identifier).")
            logger.debug(f"Using user-specified electrumsv data dir ({id})")

        elif self.is_not_new_and_id(id, new):
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            if not new_dir.exists():
                logger.debug(f"User-specified electrumsv data directory: {new_dir} does not exist"
                             f" and so will be created anew.")
            logger.debug(f"Using user-specified electrumsv data dir ({id})")

        elif self.is_not_new_and_no_id(id, new):
            id = DEFAULT_ID_ELECTRUMSV
            new_dir = self.app_state.electrumsv_dir.joinpath(id)
            logger.debug(f"Using default electrumsv data dir ({DEFAULT_ID_ELECTRUMSV})")

        logger.debug(f"Electrumsv data dir = {new_dir}")
        return new_dir

    def port_is_in_use(self, port) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", port))
            return False
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                logger.debug("Port is already in use")
                return True
            else:
                logger.debug(e)
        s.close()

    def get_electrumsv_port(self):
        """any port that is not currently in use"""
        port = DEFAULT_PORT_ELECTRUMSV
        while True:
            if self.port_is_in_use(port):
                port += 1
            else:
                break
        return port

    def remote_electrumsv(self, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        data_dir = self.get_component_data_dir_for_id(ComponentName.ELECTRUMSV,
            self.app_state.electrumsv_dir)
        port = self.get_electrumsv_port()
        self.app_state.update_electrumsv_data_dir(data_dir, port)

        if not self.app_state.electrumsv_dir.exists():
            logger.debug(f"Installing electrumsv (url={url})")
            self.app_state.installers.fetch_electrumsv(url, branch)

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
                logger.debug(f"Electrumsv is already installed (url={url})")
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
                logger.debug(f"Alternate fork of electrumsv is already installed")
                logger.debug(f"Moving existing fork (to '{existing_fork}.bak')")
                logger.debug(f"Installing electrumsv (url={url})")
                os.rename(
                    self.app_state.electrumsv_dir,
                    self.app_state.electrumsv_dir.with_suffix(".bak"),
                )
                self.app_state.installers.fetch_electrumsv(url, branch)

    def local_electrumsv(self, repo, branch):
        logger.debug(f"Installing local dependency for {ComponentName.ELECTRUMSV} "
                     f"at path: {repo}")
        assert Path(repo).exists(), f"the path {repo} does not exist!"
        if branch != "":
            subprocess.run(f"git checkout {branch}", shell=True, check=True)
        self.app_state.set_electrumsv_path(Path(repo))
        new_dir = self.get_component_data_dir_for_id(ComponentName.ELECTRUMSV,
            self.app_state.electrumsv_dir)
        port = self.get_electrumsv_port()
        self.app_state.update_electrumsv_data_dir(new_dir, port)

    def local_electrumx(self, repo, branch):
        logger.debug(f"Installing local dependency for {ComponentName.ELECTRUMX} "
                     f"at path: {repo}")
        assert Path(repo).exists(), f"the path {repo} does not exist!"
        if branch != "":
            subprocess.run(f"git checkout {branch}", shell=True, check=True)
        self.electrumx_dir = Path(repo)
        self.electrumx_data_dir = self.electrumx_dir.joinpath("electrumx_data")

    # ----- installation entry points ----- #
    # 1) fetch (as needed) + install packages
    # 2) generate run script

    def electrumsv(self):
        repo = self.app_state.start_options[ComponentOptions.REPO]
        branch = self.app_state.start_options[ComponentOptions.BRANCH]
        if repo == "" or repo.startswith("https://"):  # default
            repo = "https://github.com/electrumsv/electrumsv.git" if repo == "" else repo
            self.app_state.set_electrumsv_path(self.app_state.depends_dir.joinpath("electrumsv"))
            self.remote_electrumsv(repo, branch)
        else:
            self.local_electrumsv(repo, branch)

        self.app_state.installers.generate_run_scripts_electrumsv()

    def electrumx(self):
        """--repo and --branch flags affect the behaviour of the 'fetch' step"""
        repo = self.app_state.start_options[ComponentOptions.REPO]
        branch = self.app_state.start_options[ComponentOptions.BRANCH]
        if repo == "" or repo.startswith("https://"):  # default
            repo = "https://github.com/kyuupichan/electrumx.git"
            self.app_state.installers.fetch_electrumx(repo, branch)
        else:
            self.local_electrumx(repo, branch)

        self.app_state.installers.generate_run_script_electrumx()

    def node(self, branch):
        """this one has a pip installer at https://pypi.org/project/electrumsv-node/ and
        only official releases from pypi are supported"""
        repo = self.app_state.start_options[ComponentOptions.REPO]
        if not repo == "":  # default
            logger.error("ignoring --repo flag for node - not applicable.")

        self.app_state.installers.fetch_node()
        # self.app_state.install_tools.generate_run_script_node()  # N/A

    def status_monitor(self):
        """this is a locally hosted sub-repo so there is no 'fetch' step"""
        repo = self.app_state.start_options[ComponentOptions.REPO]
        if not repo == "":  # default
            logger.error("ignoring --repo flag for status_monitor - not applicable.")

        # fetch N/A - located inside of SDK
        self.app_state.installers.generate_run_script_status_monitor()

    def whatsonchain(self):
        self.fetch_whatsonchain(self.app_state.installers.app_state)
        self.app_state.installers.generate_run_script_whatsonchain()

    def indexer(self):
        raise NotImplementedError("electrumsv_indexer installation is not supported yet.")

    def init_run_script_dir(self):
        os.makedirs(self.app_state.run_scripts_dir, exist_ok=True)
        os.chdir(self.app_state.run_scripts_dir)


    # ----- GENERATE SCRIPTS ----- #

    def generate_run_scripts_electrumsv(self):
        """makes both the daemon script and a script for running the GUI"""
        self.init_run_script_dir()
        path_to_dapp_example_apps = self.app_state.electrumsv_dir.joinpath("examples").joinpath(
            "applications"
        )
        esv_env_vars = {
            "PYTHONPATH": str(path_to_dapp_example_apps),
        }
        esv_script = str(self.app_state.electrumsv_dir.joinpath("electrum-sv"))
        esv_data_dir = self.app_state.electrumsv_data_dir
        port = self.app_state.electrumsv_port
        component_args = \
            self.app_state.component_args if len(self.app_state.component_args) != 0 else None

        logger.debug(f"esv_data_dir = {esv_data_dir}")

        base_cmd = (f"{sys.executable} {esv_script}")
        if component_args:
            make_esv_custom_script(base_cmd, esv_env_vars, component_args, esv_data_dir)
        elif not self.app_state.start_options[ComponentOptions.GUI]:
            make_esv_daemon_script(base_cmd, esv_env_vars, esv_data_dir, port)
        else:
            make_esv_gui_script(base_cmd, esv_env_vars, esv_data_dir, port)

    def generate_run_script_electrumx(self):
        self.init_run_script_dir()
        electrumx_env_vars = {
            "DB_DIRECTORY": str(self.app_state.electrumx_data_dir),
            "DAEMON_URL": "http://rpcuser:rpcpassword@127.0.0.1:18332",
            "DB_ENGINE": "leveldb",
            "SERVICES": "tcp://:51001,rpc://",
            "COIN": "BitcoinSV",
            "COST_SOFT_LIMIT": "0",
            "COST_HARD_LIMIT": "0",
            "MAX_SEND": "10000000",
            "LOG_LEVEL": "debug",
            "NET": "regtest",
        }

        commandline_string = (
            f"{sys.executable} {self.app_state.electrumx_dir.joinpath('electrumx_server')}"
        )
        make_shell_script_for_component(ComponentName.ELECTRUMX, commandline_string,
            electrumx_env_vars)

    def generate_run_script_status_monitor(self):
        self.init_run_script_dir()
        commandline_string = (
            f"{sys.executable} " f"{self.app_state.status_monitor_dir.joinpath('server.py')}"
        )
        make_shell_script_for_component(ComponentName.STATUS_MONITOR, commandline_string, {})

    def generate_run_script_whatsonchain(self):
        self.init_run_script_dir()

        commandline_string1 = f"cd {self.app_state.woc_dir}\n"
        commandline_string2 = f"call npm start\n" if sys.platform == "win32" else f"npm start\n"
        separate_lines = [commandline_string1, commandline_string2]
        make_shell_script_for_component(ComponentName.WHATSONCHAIN,
                                        commandline_string=None, env_vars=None, multiple_lines=separate_lines)

    # ----- INSTALL FUNCTIONS ----- #

    def fetch_electrumsv(self, url, branch):
        # Note - this is only so that it works "out-of-the-box". But for development
        # should use a dedicated electrumsv repo and specify it via cli arguments (not implemented)
        if not self.app_state.electrumsv_dir.exists():
            os.chdir(self.app_state.depends_dir)
            subprocess.run(f"git clone {url}", shell=True, check=True)

            os.chdir(self.app_state.electrumsv_dir)
            checkout_branch(branch)

            process1 = subprocess.Popen(
                f"{sys.executable} -m pip install --user -r"
                f" {self.app_state.electrumsv_requirements_path}",
                shell=True)
            process1.wait()
            process2 = subprocess.Popen(
                f"{sys.executable} -m pip install --user -r"
                f" {self.app_state.electrumsv_binary_requirements_path} ",
                shell=True)
            process2.wait()

    def fetch_electrumx(self, url, branch):
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        if not self.app_state.electrumx_dir.exists():
            logger.debug(f"Installing electrumx (url={url})")

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
                logger.debug(f"Electrumx is already installed (url={url})")
                checkout_branch(branch)
                subprocess.run(f"git pull", shell=True, check=True)
                # Todo - cannot re-install requirements dynamically because of plyvel
                #  awaiting a PR for electrumx

            if result.stdout.strip() != url:
                existing_fork = self.app_state.electrumx_dir
                logger.debug(f"Alternate fork of electrumx is already installed")
                logger.debug(f"Moving existing fork (to '{existing_fork}.bak')")
                logger.debug(f"Installing electrumsv (url={url})")
                os.rename(
                    self.app_state.electrumx_dir,
                    self.app_state.electrumx_dir.with_suffix(".bak"),
                )

        if not self.app_state.electrumx_dir.exists():
            os.makedirs(self.app_state.electrumx_dir, exist_ok=True)
            os.makedirs(self.app_state.electrumx_data_dir, exist_ok=True)
            os.chdir(self.app_state.depends_dir)
            subprocess.run(f"git clone {url}", shell=True, check=True)

            os.chdir(self.app_state.electrumx_dir)
            checkout_branch(branch)

    def fetch_node(self):
        subprocess.run(f"{sys.executable} -m pip install electrumsv-node", shell=True, check=True)

    def fetch_whatsonchain(self, url="https://github.com/AustEcon/woc-explorer.git",
                           branch=''):

        if not self.app_state.woc_dir.exists():
            os.makedirs(self.app_state.woc_dir, exist_ok=True)
            os.chdir(self.app_state.depends_dir)
            subprocess.run(f"git clone {url}", shell=True, check=True)

            os.chdir(self.app_state.woc_dir)
            checkout_branch(branch)

        os.chdir(self.app_state.woc_dir)
        process = subprocess.Popen("call npm install\n" if sys.platform == "win32"
                       else "npm install\n",
                       shell=True)
        process.wait()
        process = subprocess.Popen("call npm run-script build\n" if sys.platform == "win32"
                       else "npm run-script build\n",
                       shell=True)
        process.wait()
