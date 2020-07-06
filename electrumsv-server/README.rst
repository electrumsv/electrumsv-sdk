ElectrumSV Server
=================

::

  Licence: The Open BSV License
  Maintainers: Roger Taylor, AustEcon
  Project Lead: Roger Taylor
  Language: Python (>=3.7)
  Homepage: https://electrumsv.io/

Overview
========

This is a standalone server for access to the APIs required to run ElectrumSV. It is in no way
intended to run against mainnet, testnet or scaling testnet. It should be run against regtest
only.

Exposes APIs:

- REST-based for web-based calls.
- Websocket-based for web-based RPC.
- ElectrumSV-hosting-based for both calls and RPC (deferred).

Planned Work
============

- Add a simple initial web-based API.
