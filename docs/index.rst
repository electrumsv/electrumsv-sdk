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
development environment. As long as your Python installation places it's scripts on your path,
after you have installed the `ElectrumSV SDK <https://pypi.org/project/electrumsv-sdk/>`_
Python package, it should be available for you to use.

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

Help
============
For top level help::

    > electrumsv-sdk --help

For subcommand-specific help::

    > electrumsv-sdk start --help   # starts a component
    > electrumsv-sdk stop --help    # stops a component
    > electrumsv-sdk reset --help   # resets a component (what a 'reset' does is defined in the plugin)
    > electrumsv-sdk node --help    # accesses a running node's RPC API
    > electrumsv-sdk status --help  # cli access to an overview of component status

Start Command
===============
The start command is the most feature-rich and launches servers as background processes.
dependencies are installed on-demand at run-time (see next):

General usage::

   > electrumsv-sdk start --id=<unique_id> <component_name>

all ``--`` prefixed flags like ``--id``, ``--new``, ``--repo`` are optional but if used, must preceed
the ``component_name``.

Examples
~~~~~~~~~~
run node + electrumx + electrumsv::

   > electrumsv-sdk start node
   > electrumsv-sdk start electrumx
   > electrumsv-sdk start electrumsv

run new instances::

  > electrumsv-sdk start --new node

run new instances with user-defined --id::

  > electrumsv-sdk start --new --id=mynode2 node

specify --repo as a local path or remote git url for each component type::

   > electrumsv-sdk start --repo=G:\electrumsv electrumsv

specify --branch as either "master" or "features/my-feature-branch"

NOTE1: The sdk tool only handles a single ``component_type`` at a time (i.e. for the ``start``, ``stop``, ``reset`` commands).
NOTE2: The "optional arguments" above actually come **before** specifying the ``component_type`` e.g::

   > electrumsv-sdk start --new --id=myspecialnode node

This reserves the capability for arguments to the right hand side of the ``component_type`` to be fed to the component's underlying
commandline interface (if one exists) - this is currently only supported for the electrumsv builtin component.

   > electrumsv-sdk start --branch=master electrumsv

Stop Command
===============
Stops a component (running server/spawned processes/application - however you prefer to think of it).

General Usage::

   > electrumsv-sdk stop --id=<unique_id> OR <component_name>

Examples
~~~~~~~~~~~

   > electrumsv-sdk stop               # no args -> stops all registered components
   > electrumsv-sdk stop node          # stops all running ``node`` instances
   > electrumsv-sdk stop --id=node1    # stops only the component with unique identifier == ``node1``


Reset Command
================
resets server state. e.g.
- bitcoin node state is reset back to genesis
- electrumx state is reset back to genesis
- electrumsv RegTest wallet history is erased to match blockchain state e.g.
> electrumsv-sdk reset

Node Command
==============
Direct access to the standard bitcoin JSON-RPC interface e.g.::

   > electrumsv-sdk node help
   > electrumsv-sdk node generate 10

Coming soon (access to multiple different instances on their own rpcport's)::

   > electrumsv-sdk node --id=node2 getinfo

Status Command (to be changed)
=====================================
Returns a json dump of information about components of the SDK::

   > electrumsv-sdk status


Component ID
==========================
The default unique identifier is <component_name> + 1 i.e. node1, electrumx1, electrumsv1, whatsonchain1 etc. and
by convention we expect plugin creators to strictly tie the default port to this default identifier to keep the
SDK approachable for new users. For example these are the default mappings for the builtin components.

+----------------+-------+-------------------------------------------------------------+-----------------------------------------------------------------+
| Component Type |  Port |                       Datadir Windows                       |                          Datadir Linux                          |
+================+=======+=============================================================+=================================================================+
|      node      | 18332 | ~AppData/Local/ElectrumSV-SDK/component_datadirs/node/node1 | ~home/.electrumsv-sdk/component_datadirs/node/node1             |
+----------------+-------+-------------------------------------------------------------+-----------------------------------------------------------------+
|    electrumx   | 51001 | ~AppData/Local/ElectrumSV-SDK/component_datadirs/node/node1 | ~home/.electrumsv-sdk/component_datadirs/electrumx/electrumx1   |
+----------------+-------+-------------------------------------------------------------+-----------------------------------------------------------------+
|   electrumsv   |  9999 | ~AppData/Local/ElectrumSV-SDK/component_datadirs/node/node1 | ~home/.electrumsv-sdk/component_datadirs/electrumsv/electrumsv1 |
+----------------+-------+-------------------------------------------------------------+-----------------------------------------------------------------+
|  whatsonchain  |  3002 | Not applicable (no datadir needed for this application)     | Not applicable (no datadir needed for this application)         |
+----------------+-------+-------------------------------------------------------------+-----------------------------------------------------------------+
| status_monitor |  5000 | ~AppData/Local/ElectrumSV-SDK/component_state.json          | ~home/.electrumsv-sdk/component_state.json                      |
+----------------+-------+-------------------------------------------------------------+-----------------------------------------------------------------+


Plugin Design Model
~~~~~~~~~~~~~~~~~~~~~~~~~~
As of version 0.0.19 the SDK follows a plugin model whereby there are three layers:

- ``'builtin_components/'``  (located in site-packages/electrumsv_sdk/builtin_components
- ``'user_plugins/'``   (located in AppData/local/ElectrumSV-SDK/user_components
- ``'electrumsv_sdk_plugins/`` (local working directory)

Each layer overrides the one above it if there are any namespace clashes for a given ``component_type``
The rationale for using a plugin model is aimed at maintainability and extensibility.

To get a feel for the patterns and how to create your own plugin you can look at the ``'builtin_components/'``
as a template.

Disclaimer: Creating plugins is more the domain of software developers who are expected to have a
certain competency level and are willing to work through some technical challenges to get it working.

Most users of this SDK would be expected to merely make use of it for the ease of spinning up 1 or more RegTest
instances of bitcoin node(s) +/- manipulating the state of the RegTest environment via the various tools
provided out-of-the-box (which may or may not include using the electrumsv wallet GUI or daemon/REST API)


Other design rationale
~~~~~~~~~~~~~~~~~~~~~~~
Docker is a great tool when it comes to taking away the pains of running bare metal & cross-platform
and dealing with variability in cross-platform environments.

However, the SDK does in fact build each component from scratch, bare metal & cross-platform and as a
result is the only way to go if your production environment will also be bare metal & cross-platform.
It also lends itself to a better development experience once the plugin is made. As one example,
I like having the ability to set a breakpoint in my application code and have the spawned terminal window
halt at the breakpoint and enter the python debugger. I am not aware of a way to do this inside of
a docker container.

The python language itself is arguably the most readable and expressive scripting language that exists
and so when it comes to customizing the logic of which ports to use and spawning multiple
instances of various components that need to connect to one another... at a certain point it is
just easier to write it in a dedicated scripting language (like python)!

Of course the SDK commands can all run just fine from within a docker container if you
prefer. Or you can customize the plugin to launch a docker image with ``docker-compose up``.
Basically you have all options available to you once the plugin is configured.

(A cookie-cutter plugin for running any arbitratry docker image with ``docker-compose`` will be included soon)

Whatsonchain blockexplorer (localhost)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Please go to `Whatsonchain setup guide`_.

.. _Whatsonchain setup guide: https://github.com/electrumsv/electrumsv-sdk/tree/master/electrumsv-sdk/contrib/whatsonchain/README.md


.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

