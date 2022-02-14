"""
Warning - this will reset all components back to a blank state before running the simulation

Runs node1, servers and electrumsv1 and loads the default wallet on the daemon (so that newly
submitted blocks will be synchronized by ElectrumSV
"""
from electrumsv_sdk import commands
import logging
import requests

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("simulate-fresh-reorg")

# Stop and Reset all component types
commands.stop()
commands.reset('node')
commands.reset('simple_indexer')
commands.reset('reference_server')
commands.reset('electrumsv', deterministic_seed=True)

# Start node1 and node2
commands.start("node", component_id='node1')
commands.reset('simple_indexer', component_id='indexer1')
commands.reset('reference_server', component_id='reference1')
commands.start("electrumsv", component_id='electrumsv1')

url = f"http://127.0.0.1:9999/v1/regtest/dapp/wallets/worker1.sqlite/load_wallet"
result = requests.post(url)
result.raise_for_status()


