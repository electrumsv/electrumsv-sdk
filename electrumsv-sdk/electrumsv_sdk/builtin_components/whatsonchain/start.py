import logging

from electrumsv_node import electrumsv_node

from electrumsv_sdk.utils import get_directory_name

COMPONENT_NAME = get_directory_name(__file__)
logger = logging.getLogger(COMPONENT_NAME)


def check_node_for_woc():
    if not electrumsv_node.is_running():
        return False

    result = electrumsv_node.call_any("getinfo")
    block_height = result.json()['result']['blocks']
    if block_height == 0:
        logger.error(f"Block height=0. "
                     f"The Whatsonchain explorer requires at least 1 block to be mined. Hint: try: "
                     f"'electrumsv-sdk node generate 1'")
        return False
    return True
