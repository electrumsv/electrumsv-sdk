import aiorpcx
import asyncio
import logging
import os
import subprocess
import sys


from electrumsv_sdk.constants import SHELL_SCRIPTS_DIR
from electrumsv_sdk.constants import REMOTE_REPOS_DIR
from electrumsv_sdk.config import ImmutableConfig
from electrumsv_sdk.utils import checkout_branch


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin):
        self.plugin = plugin
        self.plugin_tools = self.plugin.plugin_tools
        self.config: ImmutableConfig = plugin.config
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def fetch_electrumx(self, url, branch):
        # Todo - make this generic with electrumx
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        if not self.plugin.src.exists():
            self.logger.debug(f"Installing electrumx (url={url})")
            os.chdir(REMOTE_REPOS_DIR)
            subprocess.run(f"git clone {url}", shell=True, check=True)

        elif self.plugin.src.exists():
            os.chdir(self.plugin.src)
            result = subprocess.run(
                f"git config --get remote.origin.url",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.stdout.strip() == url:
                self.logger.debug(f"ElectrumSV is already installed (url={url})")
                subprocess.run(f"git pull", shell=True, check=True)
                checkout_branch(branch)
            if result.stdout.strip() != url:
                existing_fork = self.plugin.src
                self.logger.debug(f"Alternate fork of electrumx is already installed")
                self.logger.debug(f"Moving existing fork (to '{existing_fork}.bak')")
                self.logger.debug(f"Installing electrumx (url={url})")
                os.rename(
                    self.plugin.src,
                    self.plugin.src.with_suffix(".bak"),
                )

    def packages_electrumx(self, url, branch):
        """plyvel wheels are not available on windows so it is swapped out for plyvel-win32 to
        make it work"""
        os.chdir(self.plugin.src)
        checkout_branch(branch)
        requirements_path = self.plugin.src.joinpath('requirements.txt')

        if sys.platform in ['linux', 'darwin']:
            process = subprocess.Popen(
                f"{sys.executable} -m pip install -r {requirements_path}", shell=True)
            process.wait()

        elif sys.platform == 'win32':
            temp_requirements = self.plugin.src.joinpath('requirements-temp.txt')
            packages = []
            with open(requirements_path, 'r') as f:
                for line in f.readlines():
                    if line.strip() == 'plyvel':
                        continue
                    packages.append(line)
            packages.append('plyvel-win32')
            with open(temp_requirements, 'w') as f:
                f.writelines(packages)
            process = subprocess.Popen(
                f"{sys.executable} -m pip install --user -r {temp_requirements}", shell=True)
            process.wait()
            os.remove(temp_requirements)

    def generate_run_script(self):
        os.makedirs(SHELL_SCRIPTS_DIR, exist_ok=True)
        os.chdir(SHELL_SCRIPTS_DIR)
        env_var_setter = 'set' if sys.platform == 'win32' else 'export'

        lines = [
            f"{env_var_setter} SERVICES="f"{f'tcp://:{self.plugin.port},rpc://'}",
            f"{env_var_setter} DB_DIRECTORY={self.plugin.datadir}",
            f"{env_var_setter} DAEMON_URL={self.plugin.DAEMON_URL}",
            f"{env_var_setter} DB_ENGINE={self.plugin.DB_ENGINE}",
            f"{env_var_setter} COIN={self.plugin.COIN}",
            f"{env_var_setter} COST_SOFT_LIMIT={self.plugin.COST_SOFT_LIMIT}",
            f"{env_var_setter} COST_HARD_LIMIT={self.plugin.COST_HARD_LIMIT}",
            f"{env_var_setter} MAX_SEND={self.plugin.MAX_SEND}",
            f"{env_var_setter} LOG_LEVEL={self.plugin.LOG_LEVEL}",
            f"{env_var_setter} NET={self.plugin.NET}",
            f"{env_var_setter} ALLOW_ROOT={self.plugin.ALLOW_ROOT}",
            f"{sys.executable} {self.plugin.src.joinpath('electrumx_server')}"
        ]
        self.plugin_tools.make_shell_script_for_component(list_of_shell_commands=lines,
            component_name=self.plugin.COMPONENT_NAME)

    async def is_electrumx_running(self):
        for sleep_time in (1, 2, 3):
            try:
                self.logger.debug("Polling electrumx...")
                async with aiorpcx.connect_rs(host="127.0.0.1", port=self.plugin.port)\
                        as session:
                    result = await session.send_request("server.version")
                    if result[1] == "1.4":
                        return True
            except Exception as e:
                pass

            await asyncio.sleep(sleep_time)
        return False
