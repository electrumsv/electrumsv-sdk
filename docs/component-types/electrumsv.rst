ElectrumSV
================
Automates the running of the ElectrumSV wallet in 'daemon mode' with the example
REST API 'dapp' (daemon app) loaded and accessible on localhost (functions like a plugin).

REST API documentation is available here:
https://electrumsv.readthedocs.io/en/sv-1.3.11/building-on-electrumsv/rest-api.html


Depends on these components:

- node
- electrumx

So start these components first.


To run in daemon mode do::

    # In a new terminal window
    electrumsv-sdk start electrumsv

    OR

    # Print to current shell
    electrumsv-sdk start --inline electrumsv

    OR

    # As a background process (required for CI/CD or a headless server)
    electrumsv-sdk start --background electrumsv


You can also run the ElectrumSV GUI in RegTest mode via::

    # In a new terminal window
    electrumsv-sdk start --gui electrumsv

    OR

    # Print to current shell
    electrumsv-sdk start --gui --inline electrumsv

    OR

    # As a background process (required for CI/CD or a headless server)
    electrumsv-sdk start --gui --background electrumsv


For testnet run any of the same commands above but including the ``--testnet`` flag::

    electrumsv-sdk start --gui --testnet electrumsv

