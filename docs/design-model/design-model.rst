Plugin Design Model
==========================
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


Docker & Other design rationale
================================
Docker images of each component are available from dockerhub: https://hub.docker.com/u/electrumsvsdk
and can be configured via environment variables in the docker-compose (further documentation coming).

These images are created by merely running the SDK component types inside of docker.

Basically you have all options available to you once the plugin is configured.