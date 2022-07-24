ElectrumSV Server
=================

::

  Licence: The Open BSV License
  Maintainers: Roger Taylor, AustEcon
  Project Lead: Roger Taylor
  Language: Python (>=3.9)
  Homepage: https://electrumsv.io/

Overview
========

At present, this is a standalone server to act as a mock DPP (Direct Payment Protocol) with
a connected payee merchant wallet. It also has a mock merchant website for creating purchase
orders. It is in no way intended to run against mainnet, testnet or scaling testnet.
It should be run against regtest only.

It broadcasts the DPP Payment to mAPI and provides the details for a newly
created peer channel for the mAPI callback.

This server is therefore used for functional testing of the ElectrumSV wallet when it is
acting as the **payee**.

Exposed APIs:

- DPP merchant payment server.
