import logging
import os
import pathlib
import platform
import tarfile

import requests
import sys
import zipfile
from typing import Dict, Any
from urllib.parse import urlparse

from electrumsv_sdk.config import Config
from electrumsv_sdk.utils import get_directory_name


VERSION = "2.0.4"  # standalone-build-release
HEADER_SV_VERSION = "2.0.4"
MODULE_DIR = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)



# The uri is copied from the Github repository release assets list.
PREBUILT_ENTRIES = {
    "Darwin": {
        "uri": f"https://github.com/electrumsv/header-sv-binaries/releases/"
               f"download/{VERSION}/headerSV-boot-{HEADER_SV_VERSION}.zip",
        "exe": f"app-boot-{HEADER_SV_VERSION}/lib/headersv-app-{HEADER_SV_VERSION}.jar",
        "dirname": "MacOSXHeaderSV",
        "jre_uri": "https://github.com/adoptium/temurin17-binaries/releases/"
                   "download/jdk-17.0.2%2B8/OpenJDK17U-jre_x64_mac_hotspot_17.0.2_8.tar.gz",
        "jre_path": "jdk-17.0.2+8-jre/Contents/Home/bin/java",
        "jre_dirname": "jdk-17.0.2+8-jre"
    },
    "Linux": {
        "uri": f"https://github.com/electrumsv/header-sv-binaries/releases/"
               f"download/{VERSION}/headerSV-boot-{HEADER_SV_VERSION}.zip",
        "exe": f"app-boot-{HEADER_SV_VERSION}/lib/headersv-app-{HEADER_SV_VERSION}.jar",
        "dirname": "LinuxHeaderSV",
        "jre_uri": "https://github.com/adoptium/temurin17-binaries/releases/"
                   "download/jdk-17.0.3%2B7/OpenJDK17U-jre_x64_linux_hotspot_17.0.3_7.tar.gz",
        "jre_path": "jdk-17.0.3+7-jre/bin/java",
        "jre_dirname": "jdk-17.0.3+7-jre"
    },
    "Windows": {
        "uri": f"https://github.com/electrumsv/header-sv-binaries/releases/download/{VERSION}/"
               f"headerSV-boot-{HEADER_SV_VERSION}.zip",
        "exe": f"app-boot-{HEADER_SV_VERSION}/lib/headersv-app-{HEADER_SV_VERSION}.jar",
        "dirname": "WindowsHeaderSV",
        "jre_uri": "https://github.com/adoptium/temurin17-binaries/releases/"
                   "download/jdk-17.0.2%2B8/OpenJDK17U-jre_x64_windows_hotspot_17.0.2_8.zip",
        "jre_path": "jdk-17.0.2+8-jre/bin/java.exe",
        "jre_dirname": "jdk-17.0.2+8-jre"
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


def download_and_install_jar(install_path: pathlib.Path) -> None:
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
    logger.debug(f"downloading HeaderSV executable from: {uri.path}")
    filename = os.path.basename(uri.path)
    os.makedirs(install_path / HEADER_SV_VERSION, exist_ok=True)
    download_path = install_path / HEADER_SV_VERSION / filename

    if not download_path.exists():
        # Download the build.
        r = requests.get(entry["uri"])
        with open(download_path, "wb") as f:
            f.write(r.content)

    # Extract the build.
    output_path = install_path / HEADER_SV_VERSION / entry['dirname']
    if not output_path.exists():
        with zipfile.ZipFile(download_path, 'r') as z:
            z.extractall(install_path / HEADER_SV_VERSION)

    if download_path.exists():
        os.remove(download_path)


def download_and_install_jre(install_path: pathlib.Path) -> None:
    """
    Identify the correct pre-built release for the running Python version and:
    - Download it if it is not already downloaded.
    - Check if the checksum of the file is correct.
    - Extract the archive to the `build` directory in the install path if
    it not already extracted.
    """
    if not install_path.exists():
        install_path.mkdir()

    entry = _get_entry()
    uri = urlparse(entry["jre_uri"])
    logger.debug(f"downloading java runtime from: {uri.path}")
    filename = os.path.basename(uri.path)
    os.makedirs(install_path, exist_ok=True)
    download_path = install_path / filename

    if not download_path.exists():
        # Download the build.
        r = requests.get(entry["jre_uri"])
        with open(download_path, "wb") as f:
            f.write(r.content)

    # Extract the build.
    output_path = install_path / entry['jre_dirname']
    if not output_path.exists():
        if entry['jre_uri'].endswith('.tar.gz'):
            with tarfile.open(download_path, 'r') as tar:
                def is_within_directory(directory, target):
                    
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    
                    return prefix == abs_directory
                
                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")
                
                    tar.extractall(path, members, numeric_owner) 
                    
                
                safe_extract(tar, install_path)

        elif entry['jre_uri'].endswith('.zip'):
            with zipfile.ZipFile(download_path, 'r') as zip:
                zip.extractall(install_path)

        else:
            logger.error("Unsupported archive format")

    if download_path.exists():
        os.remove(download_path)


def download_and_install(install_path: pathlib.Path) -> None:
    download_and_install_jar(install_path)
    download_and_install_jre(install_path)


def get_run_command(install_path: pathlib.Path) -> str:
    """
    Work out where the executable is located for the given platform/architecture.
    """
    entry = _get_entry()
    java_exe_path = install_path / entry['jre_path']
    jar_file_path = install_path / HEADER_SV_VERSION / entry['exe']
    return f"{java_exe_path.as_posix()} -jar {jar_file_path}"


def load_env_vars() -> None:
    env_vars = {
        "PYTHONUNBUFFERED": "1"
    }
    os.environ.update(env_vars)
    from dotenv import load_dotenv
    env_path = pathlib.Path(MODULE_DIR) / 'exe-config' / '.env'
    load_dotenv(dotenv_path=env_path)


if __name__ == "__main__":
    # This will download and extract the correct build to the local `zzz` directory for testing.
    os.environ['SDK_PORTABLE_MODE'] = "1"
    SDK_PORTABLE_MODE = int(os.environ['SDK_PORTABLE_MODE'])
    download_path = pathlib.Path("zzz")
    config = Config()
    download_and_install(download_path)

    run_path = get_run_command(download_path)
