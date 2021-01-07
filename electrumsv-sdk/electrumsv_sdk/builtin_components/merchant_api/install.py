import logging
import os
import pathlib
import platform
import shutil

import requests
import sys
import zipfile
from typing import Dict
from urllib.parse import urlparse

from electrumsv_sdk.utils import get_directory_name

VERSION = "0.0.1"  # electrumsv/electrumsv-mAPI version
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


def load_pfx_file(install_path, config):
    """copy the localhost.pfx specified via the --ssl-pfx commandline argument to the required
    location"""
    if hasattr(config, "ssl_pfx"):
        if os.path.isfile(config.ssl_pfx):
            src = config.ssl_pfx
            dst = pathlib.Path(MODULE_DIR) / "config/localhost.pfx"
            logger.debug(f"copying .pfx file to {dst}")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)
        else:
            logger.error(f"could not locate file at localhost.pfx file - did you mistype the path?")
            sys.exit(1)
    else:
        logger.error(f"Self-signed 'localhost.pfx' server certificate for merchant API has not "
                     f"been loaded - please generate one and load it via 'electrumsv-sdk install "
                     f"--ssl-pfx=<path/to/localhost.pfx> merchant_api")
        sys.exit(1)


def _get_entry() -> Dict:
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
    download_path = install_path / filename

    if not download_path.exists():
        # Download the build.
        r = requests.get(entry["uri"])
        with open(download_path, "wb") as f:
            f.write(r.content)

    # Extract the build.
    output_path = install_path / entry['dirname']
    if not output_path.exists():
        with zipfile.ZipFile(download_path, 'r') as z:
            z.extractall(install_path)


def load_env_vars():
    from dotenv import load_dotenv
    env_path = pathlib.Path(MODULE_DIR) / 'exe-config/.env'
    load_dotenv(dotenv_path=env_path)


def get_run_path(install_path: pathlib.Path) -> pathlib.Path:
    """
    Work out where the executable is located for the given platform/architecture.
    """
    entry = _get_entry()
    return install_path / entry["exe"]


if __name__ == "__main__":
    # This will download and extract the correct build to the local `zzz` directory for testing.
    download_path = pathlib.Path("zzz")
    download_and_install(download_path)

    run_path = get_run_path(download_path)
    assert run_path.exists(), "executable not found"
    assert run_path.is_file(), "executable is not a file"
