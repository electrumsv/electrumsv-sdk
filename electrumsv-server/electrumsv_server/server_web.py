import calendar
import datetime
from functools import partial
import logging
import json
import os
import types
from typing import Any, Dict, Optional
import uuid

import bitcoinx
from trinket import Request, Response, Trinket
from trinket.extensions import logger
from trinket.http import HTTPError, HTTPStatus

from .application import Application
from .constants import DEFAULT_PAGE
from .database import PaymentRequest, PaymentRequestOutput
from .payment_requests import get_next_script


log = logging.getLogger("server-web")


async def api_home(app: Application, request: Request, filename: Optional[str]=None) -> Response:
    if not filename: filename = DEFAULT_PAGE
    page_path = os.path.realpath(os.path.join(app.wwwroot_path, filename))
    if not page_path.startswith(app.wwwroot_path) or not os.path.exists(page_path):
        raise HTTPError(HTTPStatus.NOT_FOUND, f"<html>Page not found: {filename}</html>")

    with open(page_path, "r") as f:
        return Response.html(f.read())


async def api_bip270_payment_prepare(app: Application, request: Request) -> Response:
    data = json.loads(await request.raw_body)

    if type(data) is not dict:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "invalid payment data type")

    description = data.get("description")
    if description is not None and type(description) is not str:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "invalid payment description type")

    output_list = data.get("outputs")
    if type(output_list) is not list:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "invalid payment outputs type")

    request_uid = uuid.uuid4()
    date_created = datetime.datetime.utcnow()
    date_expires = date_created + datetime.timedelta(minutes=10)
    request = PaymentRequest(uid=request_uid, description=description,
        date_created=date_created, date_expires=date_expires)

    outputs = []
    for amount_entry in output_list:
        description, amount = amount_entry
        assert description is None or type(description) is str and len(description) < 100
        assert type(amount) is int
        script = get_next_script()
        outputs.append(PaymentRequestOutput(description=description, amount=amount,
            script=script, request=request_uid))

    with app.db.atomic():
        PaymentRequest.bulk_create([ request ])
        PaymentRequestOutput.bulk_create(outputs, batch_size=100)

    id_text = str(request_uid)
    response = {
        "request_uri":
            f"bitcoin:?r=http://127.0.0.1:{app.config.http_server_port}/api/bip270/{id_text}&sv",
        "expiry_timestamp": calendar.timegm(date_expires.utctimetuple()),
    }
    return Response.json(response)


async def api_bip270_payment_request_get(app: Application, request: Request,
        id_text: str) -> Response:
    request_id = uuid.UUID(hex=id_text)

    pr = (PaymentRequest.select(PaymentRequest, PaymentRequestOutput)
        .join(PaymentRequestOutput)
        .where(PaymentRequest.uid == request_id.bytes)).get()

    outputs_object = []
    for output in pr.outputs:
        outputs_object.append({ "description": output.description, "amount": output.amount,
            "script": output.script.hex()  })

    request_object = {
        "network": "bitcoin-sv",
        "memo": pr.description,
        "paymentUrl":
            f"http://127.0.0.1:{app.config.http_server_port}/api/bip270/{id_text}",
        "outputs": outputs_object,
        "creationTimestamp": calendar.timegm(pr.date_created.utctimetuple()),
        "expirationTimestamp": calendar.timegm(pr.date_expires.utctimetuple()),
    }
    return Response.json(request_object)


async def api_bip270_payment_request_post(app: Application, request: Request,
        id_text: str) -> Response:
    payment_object = json.loads(await request.raw_body)

    content_type = request.headers.get('Content-Type')
    if content_type != "application/bitcoinsv-payment":
        raise HTTPError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, content_type)

    accept_content_type = request.headers.get('Accept')
    if accept_content_type != "application/bitcoinsv-paymentack":
        raise HTTPError(HTTPStatus.NOT_ACCEPTABLE, accept_content_type)

    request_id = uuid.UUID(hex=id_text)
    pr = (PaymentRequest.select(PaymentRequest, PaymentRequestOutput)
        .join(PaymentRequestOutput)
        .where(PaymentRequest.uid == request_id.bytes)).get()

    # Verify that the transaction is complete.
    if type(payment_object) is not dict:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "invalid payment object")
    if "transaction" not in payment_object:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "payment object lacks transaction")

    try:
        tx = bitcoinx.Tx.from_hex(payment_object["transaction"])
    except (TypeError, ValueError):
        # TypeError: from_hex gets non string.
        # ValueError: from_hex gets invalid hex encoded data.
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Invoice has an invalid payment transaction")

    if pr.tx_hash is None:
        log.debug("Attempting to settle payment request with tx '%s'",
            tx.hex_hash())

        # Verify that the outputs are present.
        tx_outputs = { bytes(out.script_pubkey): out.value for out in tx.outputs }
        try:
            for output in pr.outputs:
                if output.amount != tx_outputs[output.script]:
                    raise HTTPError(HTTPStatus.BAD_REQUEST, "Invoice has an invalid output amount")
        except KeyError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Invoice has a missing output")

        # TODO: Broadcast it.
        # Broadcasting the transaction verifies that the transaction is valid.

        # TODO: If it fails to broadcast handle it.

        # Mark the invoice as paid by the given transaction.
        query = (PaymentRequest
            .update({ PaymentRequest.tx_hash: tx.hash() })
            .where(PaymentRequest.uid == request_id.bytes))
        query.execute()

        log.debug("Payment request '%s' paid with tx '%s'",
            request_id, tx.hex_hash())
        # TODO: Notify any connected listener.
    elif pr.tx_hash != tx.hash():
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Invoice already paid with different payment")

    ack_object = {
        "payment": payment_object,
    }
    return Response(status = HTTPStatus.OK, body = json.dumps(ack_object), headers = {
        'Content-Type': 'application/bitcoinsv-paymentack',
    })


def create(app: Application) -> Trinket:
    server = logger(Trinket())
    server.route("/")(partial(api_home, app))
    server.route("/api/bip270", ["POST"])(
        partial(api_bip270_payment_prepare, app))
    server.route("/api/bip270/{id_text}")(
        partial(api_bip270_payment_request_get, app))
    server.route("/api/bip270/{id_text}", ["POST"])(
        partial(api_bip270_payment_request_post, app))
    server.route("/{filename}")(partial(api_home, app))
    return server

