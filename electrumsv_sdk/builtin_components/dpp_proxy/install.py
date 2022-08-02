import logging
import os
import pathlib
import platform
import stat

import requests
import sys
import zipfile
from typing import Dict, Any
from urllib.parse import urlparse

from electrumsv_sdk.config import Config
from electrumsv_sdk.utils import get_directory_name


DPP_PROXY_VERSION = "0.1.11-feature-branch2"
MODULE_DIR = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)



# The uri is copied from the Github repository release assets list.
PREBUILT_ENTRIES = {
    "Darwin": {
        "uri": f"https://github.com/electrumsv/electrumsv-dpp-proxy/releases/download/"
               f"{DPP_PROXY_VERSION}/MacOSXDPPProxy.zip",
        "exe": "MacOSXDPPProxy/server",
        "dirname": "MacOSXDPPProxy",
    },
    "Linux": {
        "uri": f"https://github.com/electrumsv/electrumsv-dpp-proxy/releases/download/"
               f"{DPP_PROXY_VERSION}/LinuxDPPProxy.zip",
        "exe": "LinuxDPPProxy/server",
        "dirname": "LinuxDPPProxy",
    },
    "Windows": {
        "uri": f"https://github.com/electrumsv/electrumsv-dpp-proxy/releases/download/"
               f"{DPP_PROXY_VERSION}/WindowsDPPProxy.zip",
        "exe": "WindowsDPPProxy/server.exe",
        "dirname": "WindowsDPPProxy",
    }
}


def _get_entry() -> Dict[Any, str]:
    system_name = platform.system()
    is_64bit = sys.maxsize > 2**32
    if not is_64bit:
        logger.error("32 bit OS is not supported - use a 64 bit version of python")
        sys.exit()
    entry_key = system_name
    return PREBUILT_ENTRIES[entry_key]


def download_and_install(install_path: pathlib.Path) -> None:
    """
    Identify the correct pre-built release for the running Python version and:
    - Download it if it is not already downloaded.
    - Check if the checksum of the file is correct.
    - Extract the archive to the `build` directory in the install path if it not already extracted.
    """
    if not install_path.exists():
        install_path.mkdir()

    entry = _get_entry()
    uri = urlparse(entry["uri"])
    logger.debug(f"downloading DPP-Proxy executable from: {uri.path}")
    filename = os.path.basename(uri.path)
    os.makedirs(install_path / DPP_PROXY_VERSION, exist_ok=True)
    download_path = install_path / DPP_PROXY_VERSION / filename

    if not download_path.exists():
        # Download the build.
        r = requests.get(entry["uri"])
        with open(download_path, "wb") as f:
            f.write(r.content)

    # Extract the build.
    output_path = install_path / DPP_PROXY_VERSION / entry['dirname']
    if not output_path.exists():
        with zipfile.ZipFile(download_path, 'r') as z:
            z.extractall(install_path / DPP_PROXY_VERSION)

    if download_path.exists():
        os.remove(download_path)


def get_run_command(install_path: pathlib.Path) -> str:
    """
    Work out where the executable is located for the given platform/architecture.
    """
    entry = _get_entry()
    return str(install_path / DPP_PROXY_VERSION / entry['exe'])


def load_env_vars() -> None:
    env_vars = {
        "PYTHONUNBUFFERED": "1",
    }
    os.environ.update(env_vars)
    from dotenv import load_dotenv
    env_path = pathlib.Path(MODULE_DIR) / 'exe-config' / '.env'
    load_dotenv(dotenv_path=env_path)


def chmod_exe(install_path: pathlib.Path) -> None:
    run_path = get_run_command(install_path)
    st = os.stat(run_path)
    os.chmod(run_path, st.st_mode | stat.S_IEXEC)


if __name__ == "__main__":
    # This will download and extract the correct build to the local `zzz` directory for testing.
    os.environ['SDK_PORTABLE_MODE'] = "1"
    SDK_PORTABLE_MODE = int(os.environ['SDK_PORTABLE_MODE'])
    download_path = pathlib.Path("zzz")
    config = Config()
    download_and_install(download_path)

    run_path = get_run_command(download_path)
