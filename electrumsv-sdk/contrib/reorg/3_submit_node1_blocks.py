import logging

from electrumsv_node import electrumsv_node
from electrumsv_sdk import utils
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("simulate-fresh-reorg")


if electrumsv_node.is_node_running():
    utils.submit_blocks_from_file(node_id='node1', filepath='node1_blocks.dat')
else:
    logger.exception("node unavailable")
