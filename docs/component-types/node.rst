Node
================
A wrapper for cross-compiled (unofficial) binaries of the latest bitcoin node software
for windows, macos x and linux - see: https://github.com/electrumsv/electrumsv-node.

The intended purpose is for local and CI/CD RegTest testing and an accelerated development
iteration cycle.

Testnet is also supported (although not necessarily recommended in lieu of
traditional methodologies - usually involving a supervisor such as
systemd). But in some cases you may just want to run a testnet node on windows or
mac in short bursts to test a service against it locally with minimal configuration
hassles... In which case using the SDK may be perfectly reasonable for that (It's the
easiest way I know of).

See overview section for datadir location.

These are the default settings::

    regtest=1
    server=1
    maxstackmemoryusageconsensus=0
    excessiveblocksize=10000000000

    # TxIndex for ElectrumX indexer
    txindex=1

    # If --inline flag is set (printtoconsole=1)
    printtoconsole=1

    # JSON-RPC API
    rpcuser=rpcuser
    rpcpassword=rpcpassword
    rpcport=18332
    port=18444

    # Rest API (with basic auth the same as the RPC settings)
    rest

    # ZMQ settings for mAPI
    zmqpubrawtx=tcp://127.0.0.1:28332
    zmqpubrawblock=tcp://127.0.0.1:28332
    zmqpubhashtx=tcp://127.0.0.1:28332
    zmqpubhashblock=tcp://127.0.0.1:28332
    zmqpubinvalidtx=tcp://127.0.0.1:28332
    zmqpubdiscardedfrommempool=tcp://127.0.0.1:28332
    zmqpubremovedfrommempoolblock=tcp://127.0.0.1:28332
    invalidtxsink=ZMQ

