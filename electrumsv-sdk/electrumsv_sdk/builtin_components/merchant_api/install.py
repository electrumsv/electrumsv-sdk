import logging
import os
import pathlib
import shutil
import stat
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


def _get_deploy_dir(install_path: pathlib.Path):
    build_dir = install_path / f"mAPIv{VERSION}/merchantapi-reference-{VERSION}/src/Deploy"
    return build_dir


def _get_build_dir(install_path: pathlib.Path):
    build_dir = _get_deploy_dir(install_path) / "Build"
    return build_dir


def _get_build_script_path(install_path: pathlib.Path):
    deploy_dir = install_path / f"mAPIv{VERSION}/merchantapi-reference-{VERSION}/src/Deploy"
    if sys.platform == 'win32':
        return deploy_dir / "build.bat"
    elif sys.platform in {'linux', 'darwin'}:
        return deploy_dir / "build.sh"


def _get_dockerfile_path(install_path: pathlib.Path):
    dockerfile_path = install_path / f"mAPIv{VERSION}/merchantapi-reference-" \
                                f"{VERSION}/src/MerchantAPI/APIGateway/APIGateway.Rest/Dockerfile"
    return dockerfile_path


def _get_docker_compose_path(install_path: pathlib.Path):
    docker_compose_path = install_path / f"mAPIv" \
        f"{VERSION}/merchantapi-reference-{VERSION}/src/Deploy/Build/docker-compose.yaml"
    return docker_compose_path


def copy_env(install_path):
    dst = _get_build_dir(install_path) / ".env"
    src = pathlib.Path(MODULE_DIR) / ".env"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)


def load_pfx_file(install_path, config):
    """copy the localhost.pfx specified via the --ssl-pfx commandline argument to the required
    location"""
    if hasattr(config, "ssl_pfx"):
        if os.path.isfile(config.ssl_pfx):
            src = config.ssl_pfx
            dst = _get_build_dir(install_path) / "config/localhost.pfx"
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)
        else:
            logger.error(f"could not locate file at {config.ssl_pfx} - did you mistype the path?")
            sys.exit(1)
    else:
        logger.error(f"Self-signed 'localhost.pfx' server certificate for merchant API has not "
                     f"been loaded - please generate one and load it via 'electrumsv-sdk install "
                     f"--ssl-pfx=<path/to/localhost.pfx> merchant_api")
        sys.exit(1)


def _pfx_present(install_path):
    pfx_path = _get_build_dir(install_path) / "config/localhost.pfx"
    if os.path.exists(pfx_path):
        return True
    else:
        return False


def _remove_prior_docker_compose(install_path):
    docker_compose_path = _get_docker_compose_path(install_path)
    if os.path.isfile(docker_compose_path):
        os.remove(docker_compose_path)


def _overwrite_build_script(install_path):
    build_script_path = _get_build_script_path(install_path)
    if sys.platform == 'win32':
        src = pathlib.Path(MODULE_DIR) / "build.bat"
        shutil.copy(src=src, dst=build_script_path)
    elif sys.platform in {'linux', 'darwin'}:
        src = pathlib.Path(MODULE_DIR) / "build.sh"
        shutil.copy(src=src, dst=build_script_path)
        st = os.stat(build_script_path)
        os.chmod(build_script_path, st.st_mode | stat.S_IEXEC)


def _is_azure_pipeline():
    if os.environ.get("AGENT_NAME"):
        logger.debug("detected Azure pipeline environment!")
        return True
    else:
        return False


def copy_run(install_path):
    dst = _get_deploy_dir(install_path) / "run.ps1"
    src = pathlib.Path(MODULE_DIR) / "run.ps1"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)


def _maybe_configure_for_azure_pipeline(install_path):
    """On windows Azure this will overwrite the Dockerfile to use a multi-arch base image (no other
    logic is altered)

    The template-docker-compose.yml is also overwritten to use a windows-friendly postgres image

    This is to keep Azure pipelines happy (which can only use windows type
    containers on a windows agent)
    """
    dockerfile_path = _get_dockerfile_path(install_path)
    template_docker_compose_path = _get_deploy_dir(install_path)
    if sys.platform == 'win32' and _is_azure_pipeline():
        src = pathlib.Path(MODULE_DIR) / "Dockerfile"
        shutil.copy(src=src, dst=dockerfile_path)

        src = pathlib.Path(MODULE_DIR) / "template-docker-compose.yml"
        shutil.copy(src=src, dst=template_docker_compose_path)

        copy_run(install_path)

    else:
        pass
        # and use linux type containers on windows desktop too


def build_dockerfile(install_path, config):
    # modify configuration files
    if not _pfx_present(install_path):
        load_pfx_file(install_path, config)

    build_script_path = _get_build_script_path(install_path)
    _overwrite_build_script(install_path)

    if sys.platform == 'win32':
        line = f"{build_script_path}"
    elif sys.platform in {'linux', 'darwin'}:
        line = f"/bin/bash -c \'{build_script_path}\'"

    _remove_prior_docker_compose(install_path)
    _maybe_configure_for_azure_pipeline(install_path)

    # need to be in the same working directory as the shell script for it to work
    os.chdir(os.path.dirname(build_script_path))
    process = subprocess.Popen(line, shell=True)
    process.wait()

    copy_env(install_path)  # loads SDK default configuration for mAPI
