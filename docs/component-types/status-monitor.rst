Status Monitor (Experimental)
===========================================
This component is still immature but is designed to be
standalone process that exposes an API (and websocket)
for status notifications about changes in the state of
any other running component.

NOTE: Do not use the REST API - it is not fit for public
consumption yet.

But the cli interface can be used for
getting basic information about each component (such
as the log file location)

Possible states:

- Running
- Stopped
- Failed

There is also a simple backing store (actually just a
json file with a file lock protecting it)... which can
be accessed any time via the cli::

    electrumsv-sdk status
