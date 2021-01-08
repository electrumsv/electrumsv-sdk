.. ElectrumSV SDK documentation master file, created by
   sphinx-quickstart on Wed Oct 21 19:15:52 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


ElectrumSV Software Development Kit
===================================

:Licence: The Open BSV License
:Maintainers: Roger Taylor, AustEcon
:Project Lead: Roger Taylor
:Language: Python (>=3.7)
:Homepage: https://github.com/electrumsv/electrumsv-sdk

Overview
========

This project provides a consolidated set of resources that together can allow a developer, whether
working on ElectrumSV or on any other bitcoin application, to develop, run and test
while offline (and is especially aimed at facilitating rigourous CI/CD functional testing).

The ElectrumSV SDK provides the command-line tool ``electrumsv-sdk`` to manage a local Bitcoin
development environment. As long as your Python installation places its scripts on your path,
after you have installed the `ElectrumSV SDK <https://pypi.org/project/electrumsv-sdk/>`_
Python package, it should be available for you to use.

There is full support for Windows, Linux and MacOSX


.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Getting Started

   /getting-started/installing-the-SDK
   /getting-started/help


.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Commands

   /commands/install
   /commands/start
   /commands/stop
   /commands/reset
   /commands/node
   /commands/status


.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Built in Plugins

   /built-in-plugins/overview.rst
   /built-in-plugins/whatsonchain.rst
   /built-in-plugins/node.rst
   /built-in-plugins/electrumx.rst
   /built-in-plugins/electrumsv.rst
   /built-in-plugins/merchant-api.rst
   /built-in-plugins/status-monitor.rst


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


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

