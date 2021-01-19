"""
This is only here to serve as reproducible documentation for producing reorg blocks

txid of reorged tx = a1fa9460ca105c1396cd338f7fa202bf79a9d244d730e91e19f6302a05b2f07a
"""
from electrumsv_node import electrumsv_node
from electrumsv_sdk import utils
from electrumsv_sdk import commands
import bitcoinx

import logging
logging.basicConfig(level=logging.DEBUG)


try:
    REGTEST_FUNDS_PRIVATE_KEY = bitcoinx.PrivateKey(
        bytes.fromhex('a2d9803c912ab380c1491d3bd1aaab34ca06742d7885a224ec8d386182d26ed2'),
        coin=bitcoinx.coin.BitcoinRegtest
    )
    slush_fund_private_key = REGTEST_FUNDS_PRIVATE_KEY.to_WIF()
    slush_fund_address = REGTEST_FUNDS_PRIVATE_KEY.public_key.to_address().to_string()

    # Stop and Reset all component types
    commands.stop()
    commands.reset()

    # Start node1 and node2
    commands.start("node", component_id='node1')
    commands.start("node", component_id='node2')

    # Cleanup from previous runs (if any)
    for filepath in ("common_blocks.dat", "node1_blocks.dat", "node2_blocks.dat"):
        try:
            utils.delete_raw_blocks_file(filepath)
        except FileNotFoundError:
            pass

    electrumsv_node.is_node_running()

    # Generate common_blocks.dat
    utils.call_any_node_rpc('generatetoaddress', 200, slush_fund_address, node_id='node1')
    utils.write_raw_blocks_to_file(filepath="common_blocks.dat", node_id='node1')

    # Submit common_blocks to node2 so that both nodes are equivalent
    utils.submit_blocks_from_file(node_id='node2', filepath='common_blocks.dat')

    # Node1: Send 100 bitcoins to ElectrumSV 1st receive address and mine 1 block
    utils.call_any_node_rpc('importprivkey', slush_fund_private_key, 'slush_fund_key',
        node_id='node1')
    txid = utils.call_any_node_rpc('sendtoaddress', "mwv1WZTsrtKf3S9mRQABEeMaNefLbQbKpg", 100,
        node_id='node1')['result']
    rawtx = utils.call_any_node_rpc('getrawtransaction', txid, node_id='node1')['result']

    utils.call_any_node_rpc('generate', 1, node_id='node1')
    utils.write_raw_blocks_to_file(filepath="node1_blocks.dat", node_id='node1')

    # Node2: Mine another empty block and **THEN** send 100 bitcoins to ElectrumSV 1st
    #   receive address and mine 1 block (will have a chain length advantage of 1)
    utils.call_any_node_rpc('importprivkey', slush_fund_private_key, 'slush_fund_key',
        node_id='node2')
    utils.call_any_node_rpc('generate', 1, node_id='node2')
    utils.call_any_node_rpc('sendrawtransaction', rawtx, node_id='node2')
    utils.call_any_node_rpc('generate', 1, node_id='node2')
    utils.write_raw_blocks_to_file(filepath="node2_blocks.dat", node_id='node2')
finally:
    commands.stop()
