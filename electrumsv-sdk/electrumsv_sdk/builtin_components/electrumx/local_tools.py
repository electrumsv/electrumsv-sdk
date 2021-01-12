import aiorpcx
import logging
import os
import subprocess
import sys

from aiorpcx import timeout_after
from electrumsv_sdk.constants import REMOTE_REPOS_DIR
from electrumsv_sdk.config import Config
from electrumsv_sdk.utils import checkout_branch


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin):
        self.plugin = plugin
        self.plugin_tools = self.plugin.plugin_tools
        self.config: Config = plugin.config
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
            process = subprocess.Popen(["git", "clone", f"{url}"])
            process.wait()

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
                process = subprocess.Popen(["git", "config", "pull.ff", "only"])
                process.wait()
                process = subprocess.Popen(["git", "pull"])
                process.wait()
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
            if sys.platform == 'darwin':
                # so that plyvel dependency can build wheel
                process = subprocess.Popen(["brew", "install", "leveldb"])
                process.wait()
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

    async def stop_electrumx(self, rpcport: int=8000):
        try:
            async with timeout_after(5):
                async with aiorpcx.connect_rs(host="127.0.0.1", port=rpcport)\
                        as session:
                    result = await session.send_request("stop")
                    if result:
                        return True
        except Exception as e:
            self.logger.error(f"Could not connect to ElectrumX: {e}")
            return False
