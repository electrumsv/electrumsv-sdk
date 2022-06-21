import json
import logging
import threading
import time
import requests


class MerchantAPIUnavailableError(Exception):
    pass


class AddNodeThread(threading.Thread):

    def __init__(self, mapi_url: str, max_wait_time: int) -> None:
        threading.Thread.__init__(self, daemon=True)
        self.logger = logging.getLogger("add-node-thread")
        self.start_time = time.time()
        self.wait_time = max_wait_time

        self.mapi_url = mapi_url
        self.mapi_get_info = mapi_url + "/mapi/feeQuote"
        self.mapi_add_node = mapi_url + "/api/v1/Node"

    def add_node_until_successful(self):
        """Keeps trying to connect until the mAPI service has fully started up
        (up to a max wait time)."""
        headers = {
            'Api-Key': 'apikey',
            'Content-Type': 'application/json'
        }
        body = {
            "id": "127.0.0.1:18332",
            "username": "rpcuser",
            "password": "rpcpassword",
            "remarks": "remarks"
        }
        while True:
            result = None
            try:
                result = requests.post(self.mapi_add_node, data=json.dumps(body),
                    headers=headers, timeout=5)
                if result.status_code not in {409, 200}:
                    result.raise_for_status()
                self.logger.info(f"Successfully added the node: {'127.0.0.1:18332'} to the mAPI")
                return True
            except Exception as e:
                if result:
                    self.logger.exception(f"Unexpected exception connecting to mAPI. "
                                          f"Reason: {result.content}")
                else:
                    self.logger.exception("Unexpected exception connecting to mAPI")
            if time.time() >= self.start_time + self.wait_time:
                raise MerchantAPIUnavailableError(f"The merchant API is still unreachable after "
                    f"{self.wait_time} seconds")
            time.sleep(1)

    def run(self):
        self.add_node_until_successful()
