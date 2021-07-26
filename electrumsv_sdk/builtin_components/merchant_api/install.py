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

from electrumsv_sdk.utils import get_directory_name

VERSION = "0.0.2"  # electrumsv/electrumsv-mAPI version
MERCHANT_API_VERSION = "1.3.0"
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PFX_PATH = pathlib.Path(MODULE_DIR) / "config/localhost.pfx"

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


# The uri is copied from the Github repository release assets list.
PREBUILT_ENTRIES = {
    "Darwin": {
        "uri": f"https://github.com/electrumsv/electrumsv-mAPI/releases/download/{VERSION}/"
               "MacOSXMerchantAPI.zip",
        "exe": "MacOSXMerchantAPI/MerchantAPI.APIGateway.Rest",
        "dirname": "MacOSXMerchantAPI"
    },
    "Linux": {
        "uri": f"https://github.com/electrumsv/electrumsv-mAPI/releases/download/{VERSION}/"
               "LinuxMerchantAPI.zip",
        "exe": "LinuxMerchantAPI/MerchantAPI.APIGateway.Rest",
        "dirname": "LinuxMerchantAPI"
    },
    "Windows": {
        "uri": f"https://github.com/electrumsv/electrumsv-mAPI/releases/download/{VERSION}/"
               "WindowsMerchantAPI.zip",
        "exe": "WindowsMerchantAPI/MerchantAPI.APIGateway.Rest.exe",
        "dirname": "WindowsMerchantAPI"
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
    logger.debug(f"downloading mAPI executable from: {uri.path}")
    filename = os.path.basename(uri.path)
    os.makedirs(install_path / MERCHANT_API_VERSION, exist_ok=True)
    download_path = install_path / MERCHANT_API_VERSION / filename

    if not download_path.exists():
        # Download the build.
        r = requests.get(entry["uri"])
        with open(download_path, "wb") as f:
            f.write(r.content)

    # Extract the build.
    output_path = install_path / MERCHANT_API_VERSION / entry['dirname']
    if not output_path.exists():
        with zipfile.ZipFile(download_path, 'r') as z:
            z.extractall(install_path / MERCHANT_API_VERSION)


def chmod_exe(install_path: pathlib.Path) -> None:
    run_path = get_run_path(install_path)
    st = os.stat(run_path)
    os.chmod(run_path, st.st_mode | stat.S_IEXEC)


def load_env_vars() -> None:
    env_vars = {
        "PYTHONUNBUFFERED": "1"
    }
    os.environ.update(env_vars)
    from dotenv import load_dotenv
    env_path = pathlib.Path(MODULE_DIR) / 'exe-config/.env'
    load_dotenv(dotenv_path=env_path)


def get_run_path(install_path: pathlib.Path) -> pathlib.Path:
    """
    Work out where the executable is located for the given platform/architecture.
    """
    entry = _get_entry()
    return install_path / MERCHANT_API_VERSION / entry["exe"]


if __name__ == "__main__":
    # This will download and extract the correct build to the local `zzz` directory for testing.
    download_path = pathlib.Path("zzz")
    download_and_install(download_path)

    run_path = get_run_path(download_path)
    assert run_path.exists(), "executable not found"
    assert run_path.is_file(), "executable is not a file"
