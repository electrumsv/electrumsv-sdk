import os

NODE_PORT = os.environ.get("NODE_PORT")  # if None -> set by usual deterministic allocation
NODE_RPCALLOWIP = os.environ.get("NODE_RPCALLOWIP")  # else 127.0.0.1
NODE_RPCBIND = os.environ.get("NODE_RPCBIND")
