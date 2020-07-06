from typing import Any, Dict

from trinket import Request, Response, Trinket
from trinket.extensions import logger
from trinket.http import HTTPError, HTTPStatus


async def api_home(request: Request) -> Response:
    return Response.raw(b'Blank home page')


async def api_block_search(request: Request) -> Response:
    q = request.query()
    hash_hex = q.get("hash_hex", ...) # Required.
    if hash_hex is ...:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Missing argument 'hash_hex'")
    base_height = q.int("base_height", 0)
    skip_count = q.int("skip", 0)
    take_count = q.int("count", 20)
    return Response.raw(b'Blank home page')


async def api_mempool_search(request: Request) -> Response:
    q = request.query()
    hash_hex = q.get("hash_hex", ...) # Required.
    if hash_hex is ...:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Missing argument 'hash_hex'")
    start_time = q.int("start_time", -1)
    skip_count = q.int("skip", 0)
    take_count = q.int("count", 20)
    return Response.raw(b'Blank home page')


async def api_header(request: Request) -> Response:
    q = request.query()
    height = q.int("hash_hex", ...) # Required.
    checkpoint_height = q.int("start_time", -1)
    return Response.raw(b'Blank home page')


async def api_transaction(request: Request) -> Response:
    q = request.query()
    id_hex = q.get("id", ...) # Required.
    if id_hex is ...:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Missing argument 'id_hex'")
    height = q.int("height", -1)
    exclude_transaction = q.int("exclude_transaction", -1)
    return Response.raw(b'Blank home page')


def create(params: Dict[str, Any]) -> Trinket:
    server = logger(Trinket())
    server.route("/", **params)(api_home)
    server.route("/api/block-search", **params)(api_block_search)
    server.route("/api/mempool-search", **params)(api_mempool_search)
    server.route("/api/header", **params)(api_header)
    server.route("/api/transaction", **params)(api_transaction)
    return server
