"""
This script is used in order to run servers in newly created terminal windows whilst still retaining
the ability to capture both stdout & logging output to file at the same time
"""
import argparse
import base64
import json
import logging
import os
from pathlib import Path

import bitcoinx

from electrumsv_sdk.components import Component
from electrumsv_sdk.constants import DATADIR
from electrumsv_sdk.utils import spawn_inline


logger = logging.getLogger("run-inline-script")
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(name)-24s %(message)s',
    level=logging.WARNING, datefmt='%Y-%m-%d %H:%M:%S')
filelock_logger = logging.getLogger("filelock")
filelock_logger.setLevel(logging.WARNING)


def unwrap_and_unescape_text(arg: str) -> str:
    return arg.strip("\'").replace('\\"', '"')


def main() -> None:
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
    parsed_args = top_level_parser.parse_args()
    command = unwrap_and_unescape_text(parsed_args.command)
    component_info = json.loads(base64.b64decode(parsed_args.component_info).decode())
    component_info = Component.from_dict(component_info)

    component_name = component_info.component_type
    if parsed_args.env_vars_encryption_key:
        infile = DATADIR / component_name / "encrypted.env"
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
