from typing import List, Optional

import attr


@attr.s(auto_attribs=True, frozen=False)
class Config(object):
    """
    There is a 1:1 relationship between this config and each activation of the SDK cli tool.
    Will also be instantiated inside of wrappers to the install, start, stop, reset entrypoints
    for use as a python library.
    """
    namespace: Optional[str] = None
    selected_component: str = ""
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
