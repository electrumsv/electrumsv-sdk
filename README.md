ElectrumSV Software Development Kit
===================================

This project provides a consolidated set of resources that together can allow a developer, whether
working on ElectrumSV directly or on an application based on ElectrumSV, to develop, run and test
while offline (and is especially aimed at facilitating rigourous CI/CD functional testing).

    Licence: The Open BSV License
    Maintainers: Roger Taylor, AustEcon
    Project Lead: Roger Taylor
    Language: Python (>=3.9)
    Homepage: https://electrumsv.io/

[![PyPI version](https://badge.fury.io/py/electrumsv-sdk.svg)](https://badge.fury.io/py/electrumsv-sdk)
[![Build Status](https://dev.azure.com/electrumsv/ElectrumSV/_apis/build/status/electrumsv.electrumsv-sdk?branchName=master)](https://dev.azure.com/electrumsv/ElectrumSV/_apis/build/status/electrumsv.electrumsv-sdk?branchName=master)
[![Platforms](https://img.shields.io/badge/platforms-linux%20%7C%20windows%20%7C%20macos-blue)](https://img.shields.io/badge/platforms-linux%20%7C%20windows%20%7C%20macos-blue)
[![Platforms](https://img.shields.io/pypi/pyversions/electrumsv-sdk.svg?style=flat-square)](https://pypi.org/project/electrumsv-sdk)

Documentation
================
Detailed documentation is hosted [here](https://electrumsv-sdk.readthedocs.io/en/latest/)

Basic Instructions
===================
To install from [pypi](https://pypi.org/project/electrumsv-sdk/):

    > pip install --upgrade electrumsv-sdk

Now you have global access to a script called 'electrumsv-sdk.exe' from
any console window.

For help:

    > electrumsv-sdk --help

**Note: You must run ``electrumsv-sdk install <component type>`` 
first for each component type. This may require system dependencies
you also need - please read the documentation.**

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

Note: The "optional arguments" come **before** specifying the ``component_type`` e.g.:

    > electrumsv-sdk start --new --id=myspecialnode node


Docker
===================
Docker support is here: https://github.com/electrumsv/electrumsv-sdk-docker. However,
do note that we cannot promise to keep the docker support up-to-date as we are stretched
too thin and have other priorities. Nevertheless, help will be gladly accepted.

You might also find what you need here: https://github.com/jadwahab/regtest-stack. 
Please check that one out too. Jad and co. are better placed to keep up with the bleeding
edge versioning of the node, mAPI and LiteClient services as they are directly involved 
with many of those projects. They also do not have the additional python layer of 
abstraction to sort out when it comes to docker.
