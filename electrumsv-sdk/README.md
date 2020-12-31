ElectrumSV Software Development Kit
===================================

This project provides a consolidated set of resources that together can allow a developer, whether
working on ElectrumSV directly or on an application based on ElectrumSV, to develop, run and test
while offline (and is especially aimed at facilitating rigourous CI/CD functional testing).

    Licence: The Open BSV License
    Maintainers: Roger Taylor, AustEcon
    Project Lead: Roger Taylor
    Language: Python (>=3.7)
    Homepage: https://electrumsv.io/

[![PyPI version](https://badge.fury.io/py/electrumsv-sdk.svg)](https://badge.fury.io/py/electrumsv-sdk)
[![Build Status](https://dev.azure.com/electrumsv/ElectrumSV/_apis/build/status/electrumsv.electrumsv-sdk?branchName=master)](https://dev.azure.com/electrumsv/ElectrumSV/_apis/build/status/electrumsv.electrumsv-sdk?branchName=master)
[![Platforms](https://img.shields.io/badge/platforms-linux%20%7C%20windows%20%7C%20macos-blue)](https://img.shields.io/badge/platforms-linux%20%7C%20windows%20%7C%20macos-blue)
[![Platforms](https://img.shields.io/pypi/pyversions/electrumsv-sdk.svg?style=flat-square)](https://pypi.org/project/electrumsv-sdk)

Instructions
============
Official hosted documentation webpage coming soon...

To install from [pypi](https://pypi.org/project/electrumsv-sdk/) run (for general users):

    > pip install --upgrade electrumsv-sdk

Now you have global access to a script called 'electrumsv-sdk.exe' from
any console window.

For help:

    > electrumsv-sdk --help

If you want help for one of the subcommands (e.g. 'start') do:

    > electrumsv-sdk start --help

Which will show:

    usage: electrumsv-sdk start [-h] [--new] [--gui] [--background] [--inline] [--new-terminal] [--id ID] [--repo REPO] [--branch BRANCH] {electrumsv,electrumx,merchant_api,node,status_monitor,whatsonchain,whatsonchain_api} ...

    positional arguments:
      {electrumsv,electrumx,merchant_api,node,status_monitor,whatsonchain,whatsonchain_api}
                            subcommand
        electrumsv          start electrumsv
        electrumx           start electrumx
        merchant_api        start merchant_api
        node                start node
        status_monitor      start status_monitor
        whatsonchain        start whatsonchain
        whatsonchain_api    start whatsonchain_api

    optional arguments:
      -h, --help            show this help message and exit
      --new                 run a new instance with unique 'id'
      --gui                 run in gui mode (electrumsv only)
      --background          spawn in background
      --inline              spawn in current shell
      --new-terminal        spawn in a new terminal window
      --id ID               human-readable identifier for component (e.g. 'worker1_esv')
      --repo REPO           git repo as either an https://github.com url or a local git repo path e.g. G:/electrumsv (optional)
      --branch BRANCH       git repo branch (optional)

NOTE1: The sdk tool only handles a single ``component_type`` at a time (i.e. for the ``start``,
``stop`` and ``reset`` commands).

NOTE2: The "optional arguments" above come **before** specifying the ``component_type`` e.g.:

    > electrumsv-sdk start --new --id=myspecialnode node


Plugins
-------

The plugin model has three layers

- `builtin_components/`  (located in site-packages/electrumsv_sdk/builtin_components
- `user_components/`   (located in AppData/local/ElectrumSV-SDK/user_components
- `electrumsv_sdk_components` (local working directory)

Each layer overrides the one above it if there are any namespace clashes for a given ``component_type``

The rationale for using a plugin model is aimed at maintainability and extensibility.

To get a feel for the patterns and how to create your own plugin you can look at the ``'builtin_components/'``
as a template.

Disclaimer: Creating plugins is more the domain of software developers who are expected to have a
certain competency level and are willing to work through some technical challenges to get it working.

Most users of this SDK would be expected to merely make use of existing (built-in) plugins for the
ease of spinning up 1 or more RegTest instances of the offered component types and manipulating the
state of the RegTest environment via the provided tools (which may or may not make use of the
electrumsv wallet - which runs by default as a daemon process with a REST API (but can also be
run in the more familiar GUI mode).

Whatsonchain blockexplorer (localhost)
--------------------------------------
Please go to [whatsonchain setup guide](https://github.com/electrumsv/electrumsv-sdk/tree/master/electrumsv-sdk/contrib/whatsonchain/README.md) Whatsonchain setup guide

