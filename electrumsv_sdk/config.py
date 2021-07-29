from argparse import Namespace
from typing import List, Optional, Dict, Any

import attr

from electrumsv_sdk.sdk_types import SelectedComponent


class ParsedArgs(Namespace):
    namespace: Optional[str] = None
    selected_component: SelectedComponent = ""
    component_args: List[str] = []
    node_args: List[str] = []
    repo: str = ""
    branch: str = ""
    new_flag: bool = False
    gui_flag: bool = False
    background_flag: bool = False
    inline_flag: bool = False
    new_terminal_flag: bool = False
    component_id: str = ""
    cli_extension_args: Dict[str, Any] = {}
    sdk_home_dir: str = ""


@attr.s(auto_attribs=True, frozen=False)
class Config(object):
    """
    There is a 1:1 relationship between this config and each activation of the SDK cli tool.
    Will also be instantiated inside of wrappers to the install, start, stop, reset entrypoints
    for use as a python library.
    """
    namespace: Optional[str] = None
    selected_component: SelectedComponent = ""
    component_args: List[str] = []
    node_args: List[str] = []
    repo: str = ""
    branch: str = ""
    new_flag: bool = False
    gui_flag: bool = False
    background_flag: bool = False
    inline_flag: bool = False
    new_terminal_flag: bool = False
    component_id: str = ""
    cli_extension_args: Dict[str, Any] = {}
    sdk_home_dir: str = ""
