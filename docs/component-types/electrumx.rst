ElectrumX
================
Automates the configuration and running of ElectrumX:
https://github.com/kyuupichan/electrumx on any platform.

Default settings::

    SERVICES=tcp://:51001,rpc://
    DB_DIRECTORY=<standard SDK datadir location>
    DAEMON_URL=http://rpcuser:rpcpassword@127.0.0.1:18332
    DB_ENGINE=leveldb
    COIN=BitcoinSV
    COST_SOFT_LIMIT=0
    COST_HARD_LIMIT=0
    MAX_SEND MAX_SEND=10000000
    LOG_LEVEL=debug
    NET BITCOIN_NETWORK
    ALLOW_ROOT=1

Setting up a self-signed certificate for ssl was deemed to be not worth the hassle
for local testing so is not supported.
