@echo off
set DB_DIRECTORY=g:\electrumsv-sdk\sdk_depends\electrumx_data
set DAEMON_URL=http://rpcuser:rpcpassword@127.0.0.1:18332
set DB_ENGINE=leveldb
set SERVICES=tcp://:51001,rpc://
set COIN=BitcoinSV
set COST_SOFT_LIMIT=0
set COST_HARD_LIMIT=0
set MAX_SEND=10000000
set LOG_LEVEL=debug
set NET=regtest
"C:\Users\donha\AppData\Local\Programs\Python\Python38\python.exe" "g:\electrumsv-sdk\sdk_depends\electrumx\electrumx_server"
pause
