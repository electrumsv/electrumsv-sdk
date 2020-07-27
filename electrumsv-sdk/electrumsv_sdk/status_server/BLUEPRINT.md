## SDK BLUEPRINT

##### GET http://localhost:4567/status
    [
        {
            pid:            00001,
            process_name:   "esv1",
            process_type:   "electrumsv_daemon",
            endpoint:       "http://127.0.0.1:9999"
            status:         "running" ["stopped", "failed"],
            location:       "~/ElectrumSV-SDK/sdk_depends/electrumsv",
            metadata:       {
                                "wallet_dir": "..."
                                "config": "..."
                            }
            logs:           "~/ElectrumSV-SDK/sdk_depends/electrumsv/electrum_sv_data/logs"
            last_updated:   <date>
        },
        {
            pid:            00002,
            process_name:   "ex1",
            process_type:   "electrumx",
            endpoint:       "tcp://127.0.0.1:51001"
            status:         "running" ["stopped", "failed"],
            location:       "~/ElectrumSV-SDK/sdk_depends/electrumx",
            metadata:       {
                                "data_dir": "..."
                                "environment_variables": {...}
                            }
            logs:           ""
            last_updated:   <date>
        },
        {
            pid:            00003,
            process_name:   "node1",
            process_type:   "electrumsv_node",
            endpoint:       "http://127.0.0.1:18332",
            status:         "running" ["stopped", "failed"],
            location:       "~/python38/Lib/site-packages/electrumsv_node/...",
            metadata:       {
                                "data_dir": "..."
                            }
            logs:           "~/python38/Lib/site-packages/electrumsv_node/data/regtest/bitcoind.log"
            last_updated:   <date>
        }
    ]
