import abc
from pathlib import Path
from types import ModuleType
from typing import Set, Optional

from electrumsv_sdk.config import Config

import typing

from .plugin_tools import PluginTools

if typing.TYPE_CHECKING:
    from .components import Component


class AbstractPlugin(abc.ABC):

    DEFAULT_PORT: int = 54321
    RESERVED_PORTS: Set[int] = {DEFAULT_PORT}
    COMPONENT_NAME = ""
    DEFAULT_REMOTE_REPO = "https://github.com/electrumsv/electrumsv.git"

    def __init__(self, config: Config):
        self.config = config
        self.plugin_tools: PluginTools
        self.tools = None  # Todo - abstract base class for LocalTools typing

        self.src: Optional[Path] = None
        self.datadir: Optional[Path] = None
        self.id: Optional[str] = None
        self.port: Optional[int] = None
        self.component_info: Optional["Component"] = None

    def install(self):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError


class AbstractModuleType(ModuleType):
    Plugin = AbstractPlugin
