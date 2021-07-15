import builtins
import subprocess
from argparse import ArgumentParser
from pathlib import Path
from types import ModuleType
from typing import Set, Optional, List, Dict

import typing

if typing.TYPE_CHECKING:
    from electrumsv_sdk.config import Config, ParsedArgs
    from .components import Component
    from .plugin_tools import PluginTools


class AbstractPlugin:

    DEFAULT_PORT: int = 54321
    RESERVED_PORTS: Set[int] = {DEFAULT_PORT}
    COMPONENT_NAME = ""
    DEFAULT_REMOTE_REPO = "https://github.com/electrumsv/electrumsv.git"

    def __init__(self, config: "Config"):
        self.config = config
        self.plugin_tools = PluginTools(self, config)
        self.src: Optional[Path] = None
        self.datadir: Optional[Path] = None
        self.id: Optional[str] = None
        self.port: Optional[int] = None
        self.component_info: Optional["Component"] = None
        self.network: Optional[str] = None

    def install(self) -> None:
        raise NotImplementedError

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError


class AbstractModuleType(ModuleType):
    Plugin = AbstractPlugin


SubcommandIndicesType = Dict[str, List[int]]
ParserMap = Dict[str, ArgumentParser]
RawArgsMap = Dict[str, List[str]]
SubcommandParsedArgsMap = Dict[str, "ParsedArgs"]
SelectedComponent = str
SubprocessCallResult = subprocess.Popen[builtins.bytes]
