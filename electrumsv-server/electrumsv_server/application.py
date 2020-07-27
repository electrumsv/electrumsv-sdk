from argparse import Namespace
import json
import os

from .database import open_database
from .exceptions import StartupError


class Application:
    def __init__(self, config: Namespace) -> None:
        self.config = config

        wwwroot_path = self._validate_path(config.wwwroot_path)
        if not os.path.exists(os.path.join(wwwroot_path, "index.html")):
            raise StartupError(f"The wwwroot path '{wwwroot_path}' lacks an 'index.html' file.")
        self.wwwroot_path = wwwroot_path

        self.data_path = self._validate_path(config.data_path, create=True)

        self.db = open_database(self)
        self._listeners = []

    def _validate_path(self, path: str, create: bool=False) -> str:
        path = os.path.realpath(path)
        if not os.path.exists(path):
            if not create:
                raise StartupError(f"The path '{path}' does not exist.")
            os.makedirs(path)
        return path

    def register_listener(self, ws) -> None:
        self._listeners.append(ws)

    def unregister_listener(self, ws) -> None:
        self._listeners.remove(ws)

    async def notify_listeners(self, value) -> None:
        text = json.dumps(value)
        for ws in self._listeners:
            await ws.send(text)
