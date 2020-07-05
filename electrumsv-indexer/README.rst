ElectrumSV Indexer
==================

::

  Licence: The Open BSV License
  Maintainers: Roger Taylor, AustEcon
  Project Lead: Roger Taylor
  Language: Python (>=3.7)
  Homepage: https://electrumsv.io/

Overview
========

ElectrumSV requires a blockchain indexer to be accessible to provide it with blockchain state it
is interested in. This indexer is intended to provide developers and test automation with a
solution. It is not intended to serve real world wallets or applications running against public
blockchains like Mainnet, Testnet or Scaling Testnet. It is only intended to serve against a local
ephemeral blockchain in the form of the Regtest blockchain.
