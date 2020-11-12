import os

ELECTRUMX_PORT = os.environ.get("ELECTRUMX_PORT")  # if None -> set by usual deterministic allocation

DAEMON_URL = os.environ.get("DAEMON_URL") or "http://rpcuser:rpcpassword@127.0.0.1:18332"
DB_ENGINE = os.environ.get("DB_ENGINE") or "leveldb"
COIN = os.environ.get("COIN") or "BitcoinSV"
COST_SOFT_LIMIT = os.environ.get("COST_SOFT_LIMIT") or 0
COST_HARD_LIMIT = os.environ.get("COST_HARD_LIMIT") or 0
MAX_SEND = os.environ.get("MAX_SEND") or 10000000
LOG_LEVEL = os.environ.get("LOG_LEVEL") or "debug"
NET = os.environ.get("NET") or "regtest"
ALLOW_ROOT = os.environ.get("ALLOW_ROOT") or 1
