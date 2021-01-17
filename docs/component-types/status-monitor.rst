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

Which at this time merely gives an unfiltered readout
of the full json file.

::

    {   'electrumsv1': {   'component_state': 'Stopped',
                       'component_type': 'electrumsv',
                       'id': 'electrumsv1',
                       'last_updated': '2021-01-16 22:56:28',
                       'location': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\remote_repos\\electrumsv',
                       'logging_path': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\logs\\electrumsv\\electrumsv1\\16_1_2021_22_56_8.log',
                       'metadata': {   'DATADIR': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\component_datadirs\\electrumsv\\electrumsv1',
                                       'config': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\component_datadirs\\electrumsv\\electrumsv1\\regtest\\config'},
                       'pid': 2696,
                       'status_endpoint': 'http://127.0.0.1:9999'},
    'electrumx1': {   'component_state': 'Stopped',
                      'component_type': 'electrumx',
                      'id': 'electrumx1',
                      'last_updated': '2021-01-16 22:56:28',
                      'location': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\remote_repos\\electrumx',
                      'logging_path': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\logs\\electrumx\\electrumx1\\16_1_2021_16_20_43.log',
                      'metadata': {   'DATADIR': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\component_datadirs\\electrumx\\electrumx1',
                                      'rpcport': 8000},
                      'pid': 16376,
                      'status_endpoint': 'http://127.0.0.1:51001'},
    'merchant_api1': {   'component_state': 'Stopped',
                         'component_type': 'merchant_api',
                         'id': 'merchant_api1',
                         'last_updated': '2021-01-16 22:56:28',
                         'location': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\remote_repos\\merchant_api',
                         'logging_path': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\logs\\merchant_api\\merchant_api1\\16_1_2021_22_38_58.log',
                         'metadata': None,
                         'pid': 8672,
                         'status_endpoint': 'http://127.0.0.1:45111/mapi/feeQuote'},
    'node1': {   'component_state': 'Stopped',
                 'component_type': 'node',
                 'id': 'node1',
                 'last_updated': '2021-01-16 22:56:22',
                 'location': 'C:\\Users\\donha\\AppData\\Roaming\\Python\\Python38\\site-packages',
                 'logging_path': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\logs\\node\\node1\\16_1_2021_15_39_34.log',
                 'metadata': {   'DATADIR': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\component_datadirs\\node\\node1',
                                 'p2p_port': 18444,
                                 'rpcport': 18332},
                 'pid': 12352,
                 'status_endpoint': 'http://rpcuser:rpcpassword@127.0.0.1:18332'},
    'node2': {   'component_state': 'Running',
                 'component_type': 'node',
                 'id': 'node2',
                 'last_updated': '2021-01-16 03:17:25',
                 'location': 'C:\\Users\\donha\\AppData\\Roaming\\Python\\Python38\\site-packages',
                 'logging_path': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\logs\\node\\node2\\16_1_2021_3_17_25.log',
                 'metadata': {   'DATADIR': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\component_datadirs\\node\\node2',
                                 'p2p_port': 18454,
                                 'rpcport': 18342},
                 'pid': 19008,
                 'status_endpoint': 'http://rpcuser:rpcpassword@127.0.0.1:18342'},
    'status_monitor1': {   'component_state': 'Running',
                           'component_type': 'status_monitor',
                           'id': 'status_monitor1',
                           'last_updated': '2021-01-16 22:55:31',
                           'location': 'g:\\electrumsv-sdk\\electrumsv-sdk\\electrumsv_sdk\\builtin_components\\status_monitor',
                           'logging_path': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\logs\\status_monitor\\status_monitor1\\16_1_2021_22_55_31.log',
                           'metadata': None,
                           'pid': 8712,
                           'status_endpoint': 'http://rpcuser:rpcpassword@127.0.0.1:None'},
    'whatsonchain1': {   'component_state': 'Running',
                         'component_type': 'whatsonchain',
                         'id': 'whatsonchain1',
                         'last_updated': '2021-01-15 19:58:39',
                         'location': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\remote_repos\\woc-explorer',
                         'logging_path': 'C:\\Users\\donha\\AppData\\Local\\ElectrumSV-SDK\\logs\\whatsonchain\\whatsonchain1\\15_1_2021_19_58_39.log',
                         'metadata': None,
                         'pid': 20736,
                         'status_endpoint': 'http://127.0.0.1:3002'}}

Later, additional arguments will be possible to filter the result.
This feature has not been a focus of attention...