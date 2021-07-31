import asyncio
import threading

import aiorpcx
import logging
import os
import subprocess
import sys

import typing
from typing import Any, Callable, Dict
from aiorpcx import timeout_after
from electrumsv_sdk.constants import REMOTE_REPOS_DIR, PYTHON_LIB_DIR
from electrumsv_sdk.utils import checkout_branch



if typing.TYPE_CHECKING:
    from .electrumx import Plugin


T1 = typing.TypeVar("T1")


class LocalTools:
    """helper for operating on plugin-specific state (like source dir, port, datadir etc.)"""

    def __init__(self, plugin: 'Plugin'):
        self.plugin = plugin
        self.plugin_tools = self.plugin.plugin_tools
        self.config = plugin.config
        self.logger = logging.getLogger(self.plugin.COMPONENT_NAME)

    def process_cli_args(self) -> None:
        self.plugin_tools.set_network()

    def fetch_electrumx(self, url: str, branch: str) -> None:
        # Todo - make this generic with electrumx
        """3 possibilities:
        (dir doesn't exists) -> install
        (dir exists, url matches)
        (dir exists, url does not match - it's a forked repo)
        """
        assert self.plugin.src is not None  # typing bug
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

    def packages_electrumx(self, url: str, branch: str) -> None:
        """plyvel wheels are not available on windows so it is swapped out for plyvel-win32 to
        make it work"""

        def modify_requirements_for_windows_and_mac(temp_requirements):
            """replaces plyvel with plyvel-wheels"""
            packages = []
            with open(requirements_path, 'r') as f:
                for line in f.readlines():
                    if line.strip() == 'plyvel':
                        continue
                    packages.append(line)
            packages.append('plyvel-wheels')
            with open(temp_requirements, 'w') as f:
                f.writelines(packages)

        assert self.plugin.src is not None  # typing bug
        os.chdir(self.plugin.src)

        checkout_branch(branch)
        requirements_path = self.plugin.src.joinpath('requirements.txt')
        electrumx_libs_path = PYTHON_LIB_DIR / self.plugin.COMPONENT_NAME

        if sys.platform == 'linux':
            process = subprocess.Popen(
                f"{sys.executable} -m pip install --target {electrumx_libs_path} "
                f"-r {requirements_path} --upgrade", shell=True)
            process.wait()

        elif sys.platform in {'win32', 'darwin'}:
            temp_requirements = self.plugin.src.joinpath('requirements-temp.txt')
            modify_requirements_for_windows_and_mac(temp_requirements)
            process = subprocess.Popen(
                f"{sys.executable} -m pip install --target {electrumx_libs_path} "
                f"-r {temp_requirements} --upgrade", shell=True)
            process.wait()
            os.remove(temp_requirements)

    async def stop_electrumx(self, rpcport: int=8000) -> bool:
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

    def run_coroutine_ipython_friendly(self, func: Callable[..., typing.Coroutine[Any, Any, T1]],
            *args: Any, **kwargs: Dict[Any, Any]) -> Any:
        """https://stackoverflow.com/questions/55409641/
        asyncio-run-cannot-be-called-from-a-running-event-loop"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            coro = func(*args, **kwargs)
            result = asyncio.run(coro)
            return result
        if loop and loop.is_running():
            thread = RunThread(func, args, kwargs)
            thread.start()
            thread.join()
            return thread.result


class RunThread(threading.Thread):
    def __init__(self, func: Callable[..., typing.Coroutine[Any, Any, T1]], args: Any,
            kwargs: Dict[Any, Any]) -> None:
        self.func = func
        self.args = args
        self.kwargs = kwargs
        super().__init__()

    def run(self) -> None:
        self.result = asyncio.run(self.func(*self.args, **self.kwargs))

