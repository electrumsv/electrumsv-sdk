Stop Command
===============
Stops a component (running server/spawned processes/application - however you prefer to think of it).

General Usage::

   > electrumsv-sdk stop --id=<unique_id>
   OR
   > electrumsv-sdk stop <component_name>

Examples
~~~~~~~~~~~
::

   > electrumsv-sdk stop               # no args -> stops all registered components
   > electrumsv-sdk stop node          # stops all running ``node`` instances
   > electrumsv-sdk stop --id=node1    # stops only the component with unique identifier == ``node1``