import hashlib
import json
import logging
import os
import pathlib
import platform
import requests
import sys
import tarfile
from typing import Dict
from urllib.parse import urlparse

from electrumsv_sdk.utils import get_directory_name

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


# The uri is copied from the Github repository release assets list.
# The checksums are manually copied from the Github release checksums file.
# The executable name is manually observed in the build file.
PREBUILT_ENTRIES = {
    ("Darwin", True): {
        "uri": "https://github.com/bitcoin-sv/merchantapi-reference/releases/download/v1.1.0/"
               "mapi_1.1.0_Darwin_x86_64.tar.gz",
        "sha256": "0003e702c7cd10a56cf1f8e89cc01d0492e8102d9ffd753d263058848aba85cd",
        "exe": "mapi-v1.1.0"
    },
    ("Linux", True): {
        "uri": "https://github.com/bitcoin-sv/merchantapi-reference/releases/download/v1.1.0/"
               "mapi_1.1.0_Linux_x86_64.tar.gz",
        "sha256": "52af50b4899278038f2475b229b98340eb5ac1f9e5630b885820624ec9cdb0c8",
        "exe": "mapi-v1.1.0"
    },
    ("Windows", False): {
        "uri": "https://github.com/bitcoin-sv/merchantapi-reference/releases/download/v1.1.0/"
               "mapi_1.1.0_Windows_i386.tar.gz",
        "sha256": "650d6e6916ff8afbc3be4a1a366bf4c49f215ad01eee98e5488b4c035419923b",
        "exe": "mapi-v1.1.0.exe"
    },
    ("Windows", True): {
        "uri": "https://github.com/bitcoin-sv/merchantapi-reference/releases/download/v1.1.0/"
               "mapi_1.1.0_Windows_x86_64.tar.gz",
        "sha256": "3e36fc57a301fe6c399be82446f455d95aa7873b14d987a0193c886908d6923b",
        "exe": "mapi-v1.1.0.exe"
    },
}

FEES_JSON = [
    {
        "feeType": "standard",
        "miningFee": {
            "satoshis": 1,
            "bytes": 1
        },
        "relayFee": {
            "satoshis": 1,
            "bytes": 10
        }
    },
    {
        "feeType": "data",
        "miningFee": {
            "satoshis": 2,
            "bytes": 1000
        },
        "relayFee": {
            "satoshis": 1,
            "bytes": 10000
        }
    }
]

def _get_entry() -> Dict:
    system_name = platform.system()
    is_64bit = sys.maxsize > 2**32
    entry_key = system_name, is_64bit
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
    u = urlparse(entry["uri"])
    filename = os.path.basename(u.path)
    download_path = install_path / filename

    if not download_path.exists():
        # Download the build.
        r = requests.get(entry["uri"])
        with open(download_path, "wb") as f:
            f.write(r.content)

        # Ensure the hash matches.
        hasher = hashlib.sha256()
        with open(download_path, 'rb') as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                hasher.update(data)
        assert hasher.hexdigest() == entry["sha256"], f"File {filename} checksum does not match"

    # Extract the build.
    output_path = install_path / "build"
    if not output_path.exists():
        with tarfile.open(download_path, 'r') as z:
            z.extractall(output_path)


def _write_text(file_path: pathlib.Path, text: str) -> None:
    if file_path.exists():
        os.remove(file_path)

    with open(file_path, "w") as f:
        f.write(text)


def create_settings_file(install_path: pathlib.Path, mapi_http_port: int,
        node_http_port: int, node_rpc_username: str, node_rpc_password: str,
        node_zmq_port: int) -> None:
    """
    The Merchant API executable looks for a `settings.conf` file in the current directory
    and then goes up to the parent directory and looks there, and repeats that until it hits
    the top-level directory.
    """
    settings_text = os.linesep.join([
        f"httpAddress=127.0.0.1:{mapi_http_port}",
        "bitcoin_count=1",
        "bitcoin_1_host=127.0.0.1",
        f"bitcoin_1_port={node_http_port}",
        f"bitcoin_1_username={node_rpc_username}",
        f"bitcoin_1_password={node_rpc_password}",
        f"bitcoin_1_zmqport={node_zmq_port}",
        f"quoteExpiryMinutes=10",
    ])
    _write_text(install_path / "settings.conf", settings_text)

    fees_json_text = json.dumps(FEES_JSON)
    _write_text(install_path / "fees.json", fees_json_text)


def get_run_path(install_path: pathlib.Path) -> pathlib.Path:
    """
    Work out where the executable is located for the given platform/architecture.
    """
    entry = _get_entry()
    return install_path / "build" / entry["exe"]


if __name__ == "__main__":
    # This will download and extract the correct build to the local `zzz` directory for testing.
    download_path = pathlib.Path("zzz")
    download_and_install(download_path)

    run_path = get_run_path(download_path)
    assert run_path.exists(), "executable not found"
    assert run_path.is_file(), "executable is not a file"
