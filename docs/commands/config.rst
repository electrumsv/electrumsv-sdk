Config Command
===============
To print the current json config file to console::

    electrumsv-sdk config


--sdk-home-dir
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To alter the ``SDK_HOME_DIR`` location (e.g. '``LOCALAPPDATA/ElectrumSV-SDK``' on windows)::

    electrumsv-sdk config --sdk-home-dir=<path/to/new_home_dir>

Now all SDK and components data will be stored and referenced to/from the new
location.

Note: This will likely result in the need to re-install some components because
the SDK no longer has any data for them.
