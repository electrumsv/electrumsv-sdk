Reset Command
================

General Usage::

   > electrumsv-sdk reset --id=<unique_id> <component_name>


Examples
~~~~~~~~~~~
::

   > electrumsv-sdk reset                    # no args -> resets all registered components
   > electrumsv-sdk reset node               # resets all running ``node`` instances
   > electrumsv-sdk reset --id=node1 node    # resets only the component with unique identifier == ``node1``

Behaviour for each component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+------------------+---------------------------------------+
| Component Type   | Reset Result                          |
+==================+=======================================+
| node             | deletes datadir contents              |
+------------------+---------------------------------------+
| simple_indexer   | deletes database/header files         |
+------------------+---------------------------------------+
| reference_server | deletes database file                 |
+------------------+---------------------------------------+
| electrumsv       | deletes wallet for the datadir and    |
|                  | re-creates a new one (worker1.sqlite) |
|                  | with a standard BIP32 'account'       |
|                  | (randomly generated seed)             |
+------------------+---------------------------------------+
| merchant_api     | not applicable                        |
+------------------+---------------------------------------+
| whatsonchain     | not applicable                        |
+------------------+---------------------------------------+
| whatsonchain_api | not applicable                        |
+------------------+---------------------------------------+
| status_monitor   | not applicable                        |
+------------------+---------------------------------------+

NOTE: The SDK only creates and deletes **a single wallet database (worker1.sqlite)
per datadir and there is only one datadir per instance of electrumsv.**
Please see "Component ID & Datadirs" for context.

