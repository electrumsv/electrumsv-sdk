import logging
import os
import pathlib
import shutil
import subprocess
import sys

import requests
import tarfile
from urllib.parse import urlparse

from electrumsv_sdk.utils import get_directory_name

VERSION = "1.2.0"
RELEASE_URI = f"https://github.com/bitcoin-sv/merchantapi-reference/archive/v{VERSION}.tar.gz"
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PFX_PATH = pathlib.Path(MODULE_DIR) / "config/localhost.pfx"

WIN32_SSL_CERT_SHELL_SCRIPT_PATH = pathlib.Path(MODULE_DIR) / "ssl_cert_scripts/dev_cert_gen.ps1"
UNIX_SSL_CERT_SHELL_SCRIPT_PATH = pathlib.Path(MODULE_DIR) / "ssl_cert_scripts/dev_cert_gen.sh"

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def download_and_install(install_path: pathlib.Path) -> None:
    """
    Identify the correct pre-built release for the running Python version and:
    - Download it if it is not already downloaded.
    - Check if the checksum of the file is correct.
    - Extract the archive to the `build` directory in the install path if it not already extracted.
    """
    if not install_path.exists():
        install_path.mkdir()

    u = urlparse(RELEASE_URI)
    filename = os.path.basename(u.path)
    download_path = install_path / filename

    if not download_path.exists():
        # Download the build.
        r = requests.get(RELEASE_URI)
        with open(download_path, "wb") as f:
            f.write(r.content)

    # Extract the build.
    output_path = install_path / f"mAPIv{VERSION}"
    if not output_path.exists():
        with tarfile.open(download_path, 'r') as z:
            z.extractall(output_path)


def _write_text(file_path: pathlib.Path, text: str) -> None:
    if file_path.exists():
        os.remove(file_path)

    with open(file_path, "w") as f:
        f.write(text)


def _get_build_dir(install_path: pathlib.Path):
    build_dir = install_path / f"mAPIv{VERSION}/merchantapi-reference-{VERSION}/src/Deploy/Build"
    return build_dir


def _get_build_script_path(install_path: pathlib.Path):
    deploy_dir = install_path / f"mAPIv{VERSION}/merchantapi-reference-{VERSION}/src/Deploy"
    if sys.platform == 'win32':
        return deploy_dir / "build.bat"
    elif sys.platform in {'linux', 'darwin'}:
        return deploy_dir / "build.sh"


def _get_docker_compose_path(install_path: pathlib.Path):
    docker_compose_path = install_path / f"mAPIv" \
        f"{VERSION}/merchantapi-reference-{VERSION}/src/Deploy/Build/docker-compose.yaml"
    return docker_compose_path


def copy_env(install_path):
    src = pathlib.Path(MODULE_DIR) / ".env"
    shutil.copy(src, dst=_get_build_dir(install_path))


def copy_config(install_path):
    src = pathlib.Path(MODULE_DIR) / "config/"
    config_path = _get_build_dir(install_path) / "config"
    os.makedirs(config_path, exist_ok=True)
    shutil.copytree(src, dst=config_path)


def _pfx_and_cer_present():
    if os.path.exists(PFX_PATH):
        return True
    else:
        return False


def build_dockerfile(install_path):
    # modify configuration files
    copy_env(install_path)
    if _pfx_and_cer_present():
        copy_config(install_path)
    else:
        logger.error(f"Self-signed certificate 'localhost.pfx' file does not exist - please see "
                     f"documentation")
        sys.exit(1)

    build_script_path = _get_build_script_path(install_path)
    if sys.platform == 'win32':
        # there is a bug in the build script at present so replace with working copy
        src = pathlib.Path(MODULE_DIR) / "build.bat"
        shutil.copy(src=src, dst=build_script_path)

    if sys.platform == 'win32':
        line = f"{build_script_path}"
    elif sys.platform in {'linux', 'darwin'}:
        line = f"/bin/bash -c \'{build_script_path}\'"

    # need to be in the same working directory as the shell script for it to work
    os.chdir(os.path.dirname(build_script_path))
    process = subprocess.Popen(line, shell=True)
    process.wait()


if __name__ == "__main__":
    # This will download and extract the correct build to the local `zzz` directory for testing.
    download_path = pathlib.Path("zzz")
    download_and_install(download_path)
    build_dockerfile(download_path)
