ElectrumSV Software Development Kit
===================================

::

  Licence: The Open BSV License
  Maintainers: Roger Taylor, AustEcon
  Project Lead: Roger Taylor
  Language: Python (>=3.7)
  Homepage: https://electrumsv.io/

Overview
========

This project provides a consolidated set of resources that together can allow a developer, whether
working on ElectrumSV directly or on an application based on ElectrumSV, to develop, run and test
while offline.

Instructions
============
This project is still in early stages. However, to test it out
in this early stage of development you can do
(from the top-level directory of this repository)::

    > pip install -e .

(the '-e' flag is for installing in development 'editable' mode).
Now you have global access to a script called 'electrumsv-sdk.exe' from
any console window. Now do::

    > electrumsv-sdk

Which will run the default 'full-stack' of:

- electrumsv (in daemon mode)
- electrumx server
- RegTest bitcoin daemon (as a background process)

**Ctrl + C** will terminate the servers cleanly and close the newly opened console windows.

For help::

    > electrumsv-sdk --help

Which (on 24/07/2020) will show::

    top-level
    =========
    electrumsv-sdk has four top-level namespaces (and works similarly to systemctl):
    - "start"
    - "stop"
    - "reset"
    - "node"

    The "start" command is the most feature-rich and launches servers as background
    processes (see next):

    start
    =====
    examples:
    run electrumsv + electrumx + electrumsv-node
        > electrumsv-sdk start --full-stack or
        > electrumsv-sdk start --esv-ex-node

    run electrumsv + electrumsv-indexer + electrumsv-node
        > electrumsv-sdk start --esv-idx-node

     -------------------------------------------------------
    | esv = electrumsv daemon                               |
    | ex = electrumx server                                 |
    | node = electrumsv-node                                |
    | idx = electrumsv-indexer (with pushdata-centric API)  |
    | full-stack = defaults to 'esv-ex-node'                |
     -------------------------------------------------------

    input the needed mixture to suit your needs

    dependencies are installed on-demand at run-time

    specify a local or remote git repo and branch for each server e.g.
        > electrumsv-sdk start --full-stack electrumsv repo=G:/electrumsv branch=develop

    'repo' can take the form repo=https://github.com/electrumsv/electrumsv.git for a remote
    repo or repo=G:/electrumsv for a local dev repo

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

Mode (which servers to run)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first, "--" prefixed argument sets the "mode" of operation
(in other words which servers are required).
Only one mode can be specified.
The default is to run with ``--full-stack`` if no arguments are parsed which runs:

1) electrumsv daemon
2) electrumx
3) bitcoin daemon

But in other cases you may wish to run the electrumsv **GUI** instead
(or your own 3rd party application that only requires these two
dependencies). So you may elect to use the ``--ex-node`` flag to only run:

1) electrumx
2) bitcoin daemon.

Extension 3rd party Apps (Not implemented yet)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The second, "--" prefixed, optional argument is ``--extapp`` which will add
to the above list your own 3rd party server to be launched and terminated
alongside the others. This argument can be specified multiple times like::

    > electrumsv-sdk --extapp pathtoapp1 --extapp pathtoapp2

NOTE: must be an executable (which allows use to support any programming language)
a good example usecase for this is to run a localhost node.js block
explorer alongside this RegTest stack.

Subcommands (server-specific configurations)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
After the initial "--" prefixed, top-level arguments (that always come first),
what follows is optional server-specific configurations for:

1) electrumsv
2) electrumx
3) electrumsv_node
4) electrumsv_indexer (in development)

The syntax is to specify the name of the server followed by "-" prefixed
optional arguments like this::

    > electrumsv-sdk electrumsv -repo=https://github.com/electrumsv/electrumsv.git -branch=master


**(Remote repo):** A 'repo' beginning with "https://" is automatically installed to the 'sdk_depends/'
directory as part of this SDK - this could be a forked repository or the official repo
(which is the default anyway).

**(Local repo):** If there is no such "https://" prefix to the 'repo' argument, it is assumed to be
a filesystem path to a local development repository and so no installation or
``git pull`` is attempted - it becomes the developers responsibility for the correct
functioning of this server. But it will be launched and terminated in the usual way.

Whatsonchain blockexplorer (localhost)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Please go to `Whatsonchain setup guide`_.

.. _Whatsonchain setup guide: https://github.com/electrumsv/electrumsv-sdk/tree/master/electrumsv-sdk/contrib/whatsonchain/README.md
