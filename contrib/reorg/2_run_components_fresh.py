"""
Warning - this will reset all components back to a blank state before running the simulation

Runs node1, electrumx1 and electrumsv1 and loads the default wallet on the daemon (so that newly
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
commands.reset('electrumx')
commands.reset('electrumsv', deterministic_seed=True)

# Start node1 and node2
commands.start("node", component_id='node1')
commands.start("electrumx", component_id='electrumx1')
commands.start("electrumsv", component_id='electrumsv1')

url = f"http://127.0.0.1:9999/v1/regtest/dapp/wallets/worker1.sqlite/load_wallet"
result = requests.post(url)
result.raise_for_status()


