.. ElectrumSV SDK documentation master file, created by
   sphinx-quickstart on Wed Oct 21 19:15:52 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


ElectrumSV Software Development Kit
===================================

:Licence: The Open BSV License
:Maintainers: Roger Taylor, AustEcon
:Project Lead: Roger Taylor
:Language: Python (>=3.9)
:Homepage: https://github.com/electrumsv/electrumsv-sdk

Overview
========

This project provides a consolidated set of resources that together can allow a developer, whether
working on ElectrumSV or on any other bitcoin application, to develop, run and test
while offline (and is especially aimed at facilitating rigourous CI/CD functional testing).

What Does It Do?
====================
A commandline tool that makes it very easy to spin up localhost instances of:

- Bitcoin Node
- ElectrumX
- ElectrumSV (as a daemon with a REST API or as a GUI desktop wallet)
- Merchant API
- Whatsonchain Block explorer.

.. raw:: html

   <iframe width="700" height="394" src="https://www.youtube.com/embed/z-gb-9RMJ10" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

To get started, please checkout:

- :doc:`Getting Started <../getting-started/installing-the-SDK>` documentation

There is full support for:

- Windows
- Linux
- MacOS X

Networks supported:

- Regtest
- Testnet

Why would you want this?
-------------------------

Accelerated development iteration cycle
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- If you are building an application that needs to perform SPV verification you want to know that when a block is mined, the logic is correct.
- You cannot afford to wait around 10 minutes for a block to be mined on one of the public test networks.
- Ensure correct handling of rare events like reorgs or "unmatured" coins (freshly mined coins that require 100 block confirmations before they can be moved).

CI/CD Pipeline testing
^^^^^^^^^^^^^^^^^^^^^^^

- Enough said

Benchmarking / high-throughput testing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Because, we are not supposed to do that on the standard public testnet...
- You could use the scaling testnet, but in some cases it's easier to start out with RegTest in early development and graduate to the scaling-testnet later when you're ready for it.

Solution:
^^^^^^^^^^

- With a local RegTest node, you can mine blocks on demand.
- You can run two nodes locally and simulate a reorg (we haven't added reorg simulations yet but that's coming).
- You will never have to ask for more testnet coins - just mine more blocks and top up.
- You will not be at the mercy of 3rd party service providers staying operational to continue to build and test your application.

Release Notes:
^^^^^^^^^^^^^^
See :ref:`release-notes-label`.


.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Getting Started

   /getting-started/installing-the-SDK

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Release Notes

   /release-notes/release-notes

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Commands

   /commands/help
   /commands/install
   /commands/start
   /commands/stop
   /commands/reset
   /commands/node
   /commands/status


.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Component Types

   /component-types/overview.rst
   /component-types/whatsonchain.rst
   /component-types/node.rst
   /component-types/electrumsv.rst
   /component-types/merchant-api.rst
   /component-types/status-monitor.rst


.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: User-defined plugins

   /user-defined-plugins/user-defined-plugins.rst


.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Logging

   /logging/file-logging.rst


.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Design Model

   /design-model/design-model


.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Development

   /development/testing
