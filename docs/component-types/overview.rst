Overview
============

Plugin Design Model
--------------------
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


Component ID & Datadirs
------------------------
The default unique identifier is :code:`<component_name> + 1` i.e.
:code:`node1`, :code:`simple_indexer1`, :code:`electrumsv1`, :code:`whatsonchain1` etc. and
by convention we expect plugin creators to strictly tie the default port to this default identifier to keep the
SDK approachable for new users. For example these are the default mappings for the builtin components.

The general pattern for datadirs is::

   ~AppData/Local/ElectrumSV-SDK/component_datadirs/<component_name>/<unique id>

Or on Linux::

   ~home/.electrumsv-sdk/component_datadirs/<component_name>/<unique id>

Default Component IDs and Datadirs
-----------------------------------

+------------------+-------------------+-------+---------------------------------------------------------------------------------------+------------------------------------------------------------------------------+
| Component Type   | Default ID        | Port  | Datadir Windows                                                                       | Datadir Linux                                                                |
+==================+===================+=======+=======================================================================================+==============================================================================+
| node             | node1             | 18332 | ~AppData/Local/ElectrumSV-SDK/component_datadirs/node/node1                           | ~home/.electrumsv-sdk/component_datadirs/node/node1                          |
+------------------+-------------------+-------+---------------------------------------------------------------------------------------+------------------------------------------------------------------------------+
| simple_indexer   | simple_indexer1   | 49241 | ~AppData/Local/ElectrumSV-SDK/component_datadirs/simple_indexer/simple_indexer1       | ~home/.electrumsv-sdk/component_datadirs/simple_indexer/simple_indexer1      |
+------------------+-------------------+-------+---------------------------------------------------------------------------------------+------------------------------------------------------------------------------+
| reference_server | reference_server1 | 47124 | ~AppData/Local/ElectrumSV-SDK/component_datadirs/reference_server/reference_server1   | ~home/.electrumsv-sdk/component_datadirs/reference_server/reference_server1  |
+------------------+-------------------+-------+---------------------------------------------------------------------------------------+------------------------------------------------------------------------------+
| electrumsv       | electrumsv1       | 9999  | ~AppData/Local/ElectrumSV-SDK/component_datadirs/electrumsv/electrumsv1               | ~home/.electrumsv-sdk/component_datadirs/electrumsv/electrumsv1              |
+------------------+-------------------+-------+---------------------------------------------------------------------------------------+------------------------------------------------------------------------------+
| whatsonchain     | whatsonchain1     | 3002  | Not applicable (no datadir needed for this application)                               | Not applicable (no datadir needed for this application)                      |
+------------------+-------------------+-------+---------------------------------------------------------------------------------------+------------------------------------------------------------------------------+
| whatsonchain_api | whatsonchain_api1 | 12121 | Not applicable (no datadir needed for this application)                               | Not applicable (no datadir needed for this application)                      |
+------------------+-------------------+-------+---------------------------------------------------------------------------------------+------------------------------------------------------------------------------+
| merchant_api     | merchant_api1     | 45111 | Not applicable (no datadir needed for this application)                               | Not applicable (no datadir needed for this application)                      |
+------------------+-------------------+-------+---------------------------------------------------------------------------------------+------------------------------------------------------------------------------+
| status_monitor   | status_monitor1   | 5000  | ~AppData/Local/ElectrumSV-SDK/component_state.json                                    | ~home/.electrumsv-sdk/component_state.json                                   |
+------------------+-------------------+-------+---------------------------------------------------------------------------------------+------------------------------------------------------------------------------+

MacOSX datadir location is :code:`/Users/runner/.electrumsv-sdk/component_datadirs/<component_name>`


Docker
--------------------------------
Docker images of each component are available from dockerhub: https://hub.docker.com/u/electrumsvsdk
and can be configured via environment variables in the docker-compose (further documentation coming).

These images are created by merely running the SDK component types inside of docker.
Perhaps you'd be better to use the docker images from the official sources if they
are made available but nevertheless, they are there to use at your own discretion.
