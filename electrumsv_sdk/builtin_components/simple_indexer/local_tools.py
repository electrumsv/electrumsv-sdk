import aiorpcx
import logging
import os
import subprocess
import sys

import typing
from aiorpcx import timeout_after
from electrumsv_sdk.utils import checkout_branch



if typing.TYPE_CHECKING:
    from .simple_indexer import Plugin


T1 = typing.TypeVar("T1")


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin: 'Plugin'):
        self.plugin = plugin
        self.plugin_tools = self.plugin.plugin_tools
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def fetch_simple_indexer(self, url: str, branch: str) -> None:
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        assert self.plugin.src is not None  # typing bug
        assert self.plugin.config.REMOTE_REPOS_DIR is not None  # typing bug
        cwd = os.getcwd()
        try:
            if not self.plugin.src.exists():
                self.logger.debug(f"Installing simple_indexer (url={url})")
                os.chdir(self.plugin.config.REMOTE_REPOS_DIR)
                process = subprocess.Popen(["git", "clone", f"{url}"])
                process.wait()
            elif self.plugin.src.exists():
                os.chdir(str(self.plugin.src))
                process = subprocess.Popen(["git", "pull"])
                process.wait()
                checkout_branch(branch)
        finally:
            os.chdir(cwd)


    def packages_simple_indexer(self, url: str, branch: str) -> None:
        """plyvel wheels are not available on windows so it is swapped out for plyvel-win32 to
        make it work"""

        assert self.plugin.config.PYTHON_LIB_DIR is not None
        assert self.plugin.COMPONENT_NAME is not None

        assert self.plugin.src is not None  # typing bug
        os.chdir(self.plugin.src)

        checkout_branch(branch)
        requirements_path = self.plugin.src.joinpath('requirements.txt')
        simple_indexer_libs_path = self.plugin.config.PYTHON_LIB_DIR / self.plugin.COMPONENT_NAME

        process = subprocess.Popen(
            f"{sys.executable} -m pip install --target {simple_indexer_libs_path} "
            f"-r {requirements_path} --upgrade", shell=True)
        process.wait()

    async def stop_simple_indexer(self, rpcport: int=8000) -> bool:
        try:
            async with timeout_after(5):
                async with aiorpcx.connect_rs(host="127.0.0.1", port=rpcport)\
                        as session:
                    result = await session.send_request("stop")
                    if result:
                        return True
                    else:
                        return False
        except Exception as e:
            self.logger.debug(f"Could not connect to ElectrumX: {e}")
            return False

