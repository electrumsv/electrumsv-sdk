Start Command
===============
The start command is the most feature-rich and launches servers as background processes.
dependencies are installed on-demand at run-time (see next):

General usage::

   > electrumsv-sdk start --id=<unique_id> <component_name>

all ``--`` prefixed flags like ``--id``, ``--new``, ``--repo``, ``--inline``, ``--background``,
``--new-terminal`` are optional but if used, must preceed the ``component_name``.

Examples
~~~~~~~~~~
run node + electrumx + electrumsv::

   > electrumsv-sdk start node
   > electrumsv-sdk start electrumx
   > electrumsv-sdk start electrumsv

By default, this will launch the servers with the --new-terminal flag (spawning a new console window
showing stdout/logging output).

run new instances::

  > electrumsv-sdk start --new node

run new instances with user-defined --id::

  > electrumsv-sdk start --new --id=mynode2 node

specify --repo as a local path or remote git url for each component type::

   > electrumsv-sdk start --repo=G:\electrumsv electrumsv

specify --branch as either "master" or "features/my-feature-branch"

NOTE1: The sdk tool only handles a single ``component_type`` at a time (i.e. for the ``start``, ``stop``, ``reset`` commands).
NOTE2: The "optional arguments" above come **before** specifying the ``component_type`` e.g::

   > electrumsv-sdk start --new --id=myspecialnode node

This reserves the capability for arguments to the right hand side of the ``component_type`` to be fed to the component's underlying
commandline interface (if one exists) - this is currently only supported for the electrumsv
builtin component::

   > electrumsv-sdk start --branch=master electrumsv

Run inline
~~~~~~~~~~
To run the server in the current shell (and block until exit or Ctrl + C interrupt)::

   > electrumsv-sdk start --inline <component name>

To run the server in the background::

   > electrumsv-sdk start --background <component name>

To run the server in a new terminal window (this is the default if no modifier flag is specified)::

   > electrumsv-sdk start --new-terminal <component name>