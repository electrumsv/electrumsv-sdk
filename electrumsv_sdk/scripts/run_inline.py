"""
This script is used in order to run servers in newly created terminal windows whilst still retaining
the ability to capture both stdout & logging output to file at the same time
"""
import argparse
import base64
import bitcoinx
import ctypes
import json
import logging
import os
from pathlib import Path
import sys

# Ensure that the following imports are reachable via sys.path
ELECTRUMSV_SDK_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
for idx, path in enumerate(sys.path):
    if Path(path).as_posix().lower() == ELECTRUMSV_SDK_ROOT.as_posix().lower():
        del sys.path[idx]
        sys.path.insert(0, str(ELECTRUMSV_SDK_ROOT))

from electrumsv_sdk.app_versions import APP_VERSIONS
from electrumsv_sdk.components import Component
from electrumsv_sdk.config import Config
from electrumsv_sdk.utils import spawn_inline


logger = logging.getLogger("run-inline-script")
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(name)-24s %(message)s',
    level=logging.WARNING, datefmt='%Y-%m-%d %H:%M:%S')
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)


def unwrap_and_unescape_text(arg: str) -> str:
    return arg.strip("\'").replace('\\"', '"')


def main() -> None:
    config = Config()

    top_level_parser = argparse.ArgumentParser()
    top_level_parser.add_argument("--command", type=str, default="",
        help="one contiguous string command (to run a server)")
    # On windows it is not possible to transfer more than 8192 characters via the command line.
    # For MerchantAPI there are too many environment variables and it exceeds the limit therefore
    # the env vars are written to and read from a temp file (that is encrypted with an ephemeral
    # secret key in case the file is not cleaned up and removed as expected)
    top_level_parser.add_argument("--env_vars_encryption_key", type=str, default="",
        help="ephemeral encryption key to secure environment variables in a temp file")
    top_level_parser.add_argument("--component_info", type=str, default="",
        help="component_info")
    top_level_parser.add_argument("--portable", type=str, default="0",
        help="portable mode")
    parsed_args = top_level_parser.parse_args()
    command = unwrap_and_unescape_text(parsed_args.command)
    component_info = json.loads(base64.b64decode(parsed_args.component_info).decode())
    component_info = Component.from_dict(component_info)
    is_portable_mode = parsed_args.portable
    if is_portable_mode == '1':
        os.environ['SDK_PORTABLE_MODE'] = '1'
    else:
        os.environ['SDK_PORTABLE_MODE'] = '0'

    config = Config()

    component_name = component_info.component_type
    if sys.platform == 'win32':
        app_version = APP_VERSIONS[component_name]
        title = f"{component_name} v{app_version}"
        ctypes.windll.kernel32.SetConsoleTitleW(title)

    if parsed_args.env_vars_encryption_key:
        infile = config.DATADIR / component_name / "encrypted.env"
        with open(infile, 'r') as f:
            encrypted_message = f.read()
            key = bitcoinx.PrivateKey.from_hex(parsed_args.env_vars_encryption_key)
            decrypted_message = key.decrypt_message(encrypted_message)
        env_vars = json.loads(decrypted_message)
        if Path.exists(infile):
            os.remove(infile)
    else:
        env_vars = None

    spawn_inline(command, env_vars,
        id=component_info.id, component_name=component_info.component_type,
        src=component_info.location, logfile=component_info.logging_path,
        status_endpoint=component_info.status_endpoint, metadata=component_info.metadata)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("an unexpected exception occurred")
        input("press any key to close...")
