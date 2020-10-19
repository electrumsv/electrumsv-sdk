ElectrumSV Software Development Kit
===================================

.. code-block::

  Licence: The Open BSV License
  Maintainers: Roger Taylor, AustEcon
  Project Lead: Roger Taylor
  Language: Python (>=3.7)
  Homepage: https://electrumsv.io/

Overview
========

This project provides a consolidated set of resources that together can allow a developer, whether
working on ElectrumSV directly or on an application based on ElectrumSV, to develop, run and test
while offline (and is especially aimed at facilitating rigourous CI/CD functional testing).

Instructions
============
To install from pypi_ run (for general users)::

    > pip install --upgrade electrumsv-sdk

.. _pypi: https://pypi.org/project/electrumsv-sdk/

For development of this SDK on master branch, ``cd`` to the top-level directory of this repository and do::

    > pip install -e .

(the '-e' flag is for installing in development 'editable' mode).

Now you have global access to a script called 'electrumsv-sdk.exe' from
any console window.

For help::

    > electrumsv-sdk --help

Which (on 19/10/2020) will show::

    """
    top-level
    =========
    electrumsv-sdk has four top-level namespaces (and works similarly to systemctl):
    - "start"
    - "stop"
    - "reset"
    - "node"
    - "status"

    The "start" command is the most feature-rich and launches servers as background
    processes (see next):

    start
    =====
    examples:
    run node + electrumx + electrumsv
        > electrumsv-sdk start node
        > electrumsv-sdk start electrumx
        > electrumsv-sdk start electrumsv

    run new instances:
        > electrumsv-sdk start --new node

    run new instances with user-defined --id
        > electrumsv-sdk start --new --id=myspecialnode node

    dependencies are installed on-demand at run-time

    specify --repo as a local path or remote git url for each component type.
        > electrumsv-sdk start --repo=G:\electrumsv electrumsv
    specify --branch as either "master" or "features/my-feature-branch"
        > electrumsv-sdk start --branch=master electrumsv

    all arguments are optional

    stop
    ====
    stops all running servers/spawned processes

    reset
    =====
    resets server state. e.g.
    - bitcoin node state is reset back to genesis
    - electrumx state is reset back to genesis
    - electrumsv RegTest wallet history is erased to match blockchain state e.g.
        > electrumsv-sdk reset

    node
    ====
    direct access to the standard bitcoin JSON-RPC interface e.g.
        > electrumsv-sdk node help
        > electrumsv-sdk node generate 10

    status
    ======
    returns a status report of applications previously started by the SDK

    """

if you want help for one of the subcommands do::

    > electrumsv-sdk start --help

Which on 19/10/2020 will show::

    usage: electrumsv-sdk start [-h] [--new] [--gui] [--background] [--id ID]
                                [--repo REPO] [--branch BRANCH]
                                {electrumsv,electrumx,status_monitor,node,indexer,whatsonchain}
                                ...

    positional arguments:
      {electrumsv,electrumx,status_monitor,node,indexer,whatsonchain}
                            subcommand
        electrumsv          start electrumsv
        electrumx           start electrumx
        status_monitor      start status monitor
        node                start node
        indexer             start indexer
        whatsonchain        start whatsonchain explorer

    optional arguments:
      -h, --help            show this help message and exit
      --new
      --gui
      --background
      --id ID               human-readable identifier for component (e.g.
                            'worker1_esv')
      --repo REPO           git repo as either an https://github.com url or a
                            local git repo path e.g. G:/electrumsv (optional)
      --branch BRANCH       git repo branch (optional)

NOTE1: The sdk tool only handles a single ``component_type`` at a time (i.e. for the ``start``, ``stop``, ``reset``
commands).

NOTE2: The "optional arguments" above actually come **before** specifying the ``component_type`` e.g.::

    > electrumsv-sdk start --new --id=myspecialnode node

This reserves the capability for arguments to the right hand side of the ``component_type`` to be fed to the component's underlying
commandline interface (if one exists) - this is currently only supported for the electrumsv builtin component.

Plugins
~~~~~~~
As of version 0.0.19 the SDK follows a plugin model whereby there are three layers:

- ``'builtin_components/'``  (located in site-packages/electrumsv_sdk/builtin_components
- ``'user_components/'``   (located in AppData/local/ElectrumSV-SDK/user_components
- ``'electrumsv_sdk_components'`` (local working directory)

Each layer overrides the one above it if there are any namespace clashes for a given ``component_type``

The rationale for using a plugin model is aimed at maintainability and extensibility.

To get a feel for the patterns and how to create your own plugin you can look at the ``'builtin_components/'``
as a template.

Disclaimer: Creating plugins is more the domain of software developers who are expected to have a
certain competency level and are willing to work through some technical challenges to get it working.

Most users of this SDK would be expected to merely make use of it for the ease of spinning up 1 or more RegTest
instances of bitcoin node(s) +/- manipulating the state of the RegTest environment via the various tooling (which
may or may not make use of the electrumsv wallet GUI or daemon/REST API)

Whatsonchain blockexplorer (localhost)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Please go to `Whatsonchain setup guide`_.

.. _Whatsonchain setup guide: https://github.com/electrumsv/electrumsv-sdk/tree/master/electrumsv-sdk/contrib/whatsonchain/README.md
