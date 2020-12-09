#
# This is a faux API that can be used in place of the public whatsonchain API for local testing
# development.
#
# - Whatsonchain have no authentication at this time, neither does this.
# - This just has a generic mainnet API for all networks at the moment, in reality it makes
#   no sense for it to run on mainnet as you can just use the the public one and you have
#   to run your own node.
#

import logging
import os

import requests

from aiohttp import web


SERVER_HOST = os.environ.get("SERVER_HOST") or "127.0.0.1"
SERVER_PORT = os.environ.get("SERVER_PORT") or 12121
BITCOIN_NODE_HOST = os.environ.get("BITCOIN_NODE_HOST") or "127.0.0.1"
BITCOIN_NODE_PORT = os.environ.get("BITCOIN_NODE_PORT") or 18332

PING_HOST = '127.0.0.1' if SERVER_HOST == '0.0.0.0' else SERVER_HOST
PING_URL = f"http://{PING_HOST}:{SERVER_PORT}/"


async def get_tx_hex(request: web.Request) -> web.Response:
    txid = request.match_info['txid']
    if not txid:
        raise web.HTTPBadRequest(reason="missing txid")

    uri = f"http://{BITCOIN_NODE_HOST}:{BITCOIN_NODE_PORT}/rest/tx/{txid}.hex"
    response = requests.get(uri)
    # Ensure we return what whatsonchain is expected to return for consistency. If someone wants
    # the node error text, they can check the logs for this component.
    # Whatsonchain in event of an unrecognised `txid` value:
    # - Return 404.
    # - Return no content.
    # For now we handle 200 as success and everything else like 404.
    logging.debug(
        f"Node REST request: '{uri}' status code: {response.status_code} "
        f"response text: '{response.text.strip()}'")
    response_text = response.text if response.status_code == 200 else ''
    return web.Response(status=response.status_code,
        content_type=response.headers['Content-Type'], text=response_text)


async def get_blank_page(request: web.Request) -> web.Response:
    return web.Response(text="Nothing to see here.")


def run_server() -> None:
    logging.basicConfig(level=logging.DEBUG)

    web_app = web.Application()
    web_app.add_routes([
        web.get("/", get_blank_page),
        web.get("/v1/bsv/main/tx/{txid}/hex", get_tx_hex),
    ])
    web.run_app(web_app, host=SERVER_HOST, port=SERVER_PORT) # type: ignore


if __name__ == "__main__":
    run_server()

