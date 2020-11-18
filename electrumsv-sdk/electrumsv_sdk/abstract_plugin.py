import abc
from pathlib import Path
from typing import Set, Optional

from .config import ImmutableConfig


class AbstractPlugin(abc.ABC):

    DEFAULT_PORT: int = 54321
    RESERVED_PORTS: Set[int] = {DEFAULT_PORT}
    COMPONENT_NAME = None
    DEFAULT_REMOTE_REPO = "https://github.com/electrumsv/electrumsv.git"

    def __init__(self, config: ImmutableConfig):
        self.config = config
        self.plugin_tools = None
        self.tools = None

        self.src: Optional[Path] = None
        self.datadir: Optional[Path] = None
        self.id: Optional[str] = None
        self.port: Optional[int] = None
        self.component_info: Optional["Component"] = None

    def install(self):
        raise NotImplemented

    def start(self):
        raise NotImplemented

    def stop(self):
        raise NotImplemented

    def reset(self):
        raise NotImplemented

    def status_check(self) -> Optional[bool]:
        raise NotImplemented
