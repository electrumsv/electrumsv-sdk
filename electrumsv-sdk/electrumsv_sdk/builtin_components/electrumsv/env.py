import os

ELECTRUMX_HOST = os.environ.get("ELECTRUMX_HOST") or "127.0.0.1"
ELECTRUMX_PORT = os.environ.get("ELECTRUMX_PORT") or 51001

# These are for documentation purposes only (not actually used in the plugin directly)
BITCOIN_NODE_HOST = os.environ.get("BITCOIN_NODE_HOST") or "127.0.0.1"
BITCOIN_NODE_PORT = os.environ.get("BITCOIN_NODE_PORT") or 18332
BITCOIN_NODE_RPCUSER = os.environ.get("BITCOIN_NODE_RPCUSER") or "rpcuser"
BITCOIN_NODE_RPCPASSWORD = os.environ.get("BITCOIN_NODE_RPCPASSWORD") or "rpcpassword"
RESTAPI_HOST = os.environ.get("RESTAPI_HOST")
