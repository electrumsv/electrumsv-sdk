from argparse import Namespace
import os

from bitcoinx import bip32_key_from_string

from .constants import NAME_SQLITE, XPUB_TEST
from .database import open_database
from .exceptions import StartupError
from .payment_requests import derive_pubkey


class Application:
    def __init__(self, config: Namespace) -> None:
        self.config = config

        wwwroot_path = self._validate_path(config.wwwroot_path)
        if not os.path.exists(os.path.join(wwwroot_path, "index.html")):
            raise StartupError(f"The wwwroot path '{wwwroot_path}' lacks an 'index.html' file.")
        self.wwwroot_path = wwwroot_path

        self.data_path = self._validate_path(config.data_path, create=True)

        self.db = open_database(self)

    def _validate_path(self, path: str, create: bool=False) -> str:
        path = os.path.realpath(path)
        if not os.path.exists(path):
            if not create:
                raise StartupError(f"The path '{path}' does not exist.")
            os.makedirs(path)
        return path
