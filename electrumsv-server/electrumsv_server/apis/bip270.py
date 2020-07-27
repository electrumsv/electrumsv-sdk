import calendar
import datetime
import logging
import json
import uuid
from typing import Dict

import bitcoinx
from trinket import Request, Response, websockets
from trinket.http import HTTPError, HTTPStatus
import peewee

from ..application import Application
from ..constants import RequestState
from ..database import PaymentRequest, PaymentRequestOutput
from ..payment_requests import get_next_script



log = logging.getLogger("server-apis")


async def create_invoice(app: Application, request: Request) -> Response:
    data = json.loads(await request.raw_body)

    if type(data) is not dict:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "invalid payment data type")

    description = data.get("description")
    if description is not None:
        if type(description) is not str:
            raise HTTPError(HTTPStatus.BAD_REQUEST, "invalid payment description type")
        if not description.strip():
            description = None

    output_list = data.get("outputs")
    if type(output_list) is not list:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "invalid payment outputs type")

    expiration_minutes = data.get("expiration")
    if type(expiration_minutes) is not int:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "invalid payment expiration value")

    request_uid = uuid.uuid4()
    date_created = datetime.datetime.utcnow()
    if expiration_minutes == 0:
        date_expires = None
    else:
        date_expires = date_created + datetime.timedelta(minutes=expiration_minutes)
    request = PaymentRequest(uid=request_uid, description=description,
        date_created=date_created, date_expires=date_expires, state=RequestState.UNPAID)

    database_outputs = []
    response_outputs = []
    for amount_entry in output_list:
        description, amount = amount_entry
        assert description is None or type(description) is str and len(description) < 100
        assert type(amount) is int
        script = get_next_script()
        database_outputs.append(PaymentRequestOutput(description=description, amount=amount,
            script=script, request=request_uid))
        response_outputs.append({ "description": description, "amount": amount })

    with app.db.atomic():
        PaymentRequest.bulk_create([ request ])
        PaymentRequestOutput.bulk_create(database_outputs, batch_size=100)

    return Response.json(request_uid.hex)


async def _get_invoice(app: Application, invoice_id: uuid.UUID, for_display: bool=False) -> Dict:
    pr = (PaymentRequest.select(PaymentRequest, PaymentRequestOutput)
        .join(PaymentRequestOutput)
        .where(PaymentRequest.uid == invoice_id)).get()

    outputs_object = []
    for output in pr.outputs:
        outputs_object.append({ "description": output.description, "amount": output.amount,
            "script": output.script.hex()  })

    id_text = str(invoice_id)
    paymentRequestData = {
        "network": "bitcoin-sv",
        "memo": pr.description,
        "paymentUrl":
            f"http://127.0.0.1:{app.config.http_server_port}/api/bip270/{id_text}",
        "outputs": outputs_object,
        "creationTimestamp": calendar.timegm(pr.date_created.utctimetuple()),
        "expirationTimestamp":
            calendar.timegm(pr.date_expires.utctimetuple()) if pr.date_expires else None,
    }
    if for_display:
        paymentRequestData["id"] = id_text
        paymentRequestData["state"] = pr.state
    return paymentRequestData


async def get_invoice(app: Application, request: Request, id_text: str) -> Response:
    request_id = uuid.UUID(hex=id_text)
    result = await _get_invoice(app, request_id)
    return Response.json(result)


async def get_invoice_display_state(app: Application, request: Request, id_text: str) -> Response:
    request_id = uuid.UUID(hex=id_text)
    result = {
        "paymentRequest": await _get_invoice(app, request_id, for_display=True),
        "paymentUri":
            f"bitcoin:?r=http://127.0.0.1:{app.config.http_server_port}/api/bip270/{id_text}&sv",
    }
    return Response.json(result)


async def cancel_invoice(app: Application, request: Request, id_text: str) -> Response:
    request_id = uuid.UUID(hex=id_text)

    # Mark the invoice as paid by the given transaction.
    query = (PaymentRequest
        .update({ PaymentRequest.state: RequestState.CLOSED, })
        .where(PaymentRequest.uid == request_id.bytes))
    query.execute()
    return Response.json(True)


async def submit_invoice_payment(app: Application, request: Request, id_text: str) -> Response:
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
            .update({
                PaymentRequest.tx_hash: tx.hash(),
                PaymentRequest.state: RequestState.PAID,
            })
            .where(PaymentRequest.uid == request_id.bytes))
        query.execute()

        log.debug("Payment request '%s' paid with tx '%s'",
            request_id, tx.hex_hash())

        await app.notify_listeners([ "InvoicePaid", id_text ])
        # TODO: Notify any connected listener.
    elif pr.tx_hash != tx.hash():
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Invoice already paid with different payment")

    ack_object = {
        "payment": payment_object,
    }
    return Response(status = HTTPStatus.OK, body = json.dumps(ack_object), headers = {
        'Content-Type': 'application/bitcoinsv-paymentack',
    })


async def get_invoices(app: Application, request: Request) -> Response:
    sort_order = request.query.get('order', "desc")
    offset = int(request.query.get('offset'))
    page_size = int(request.query.get('limit'))
    sort_column = request.query.get('sort', "creationTimestamp")
    filter_text = request.query.get('filter', None)

    current_page = (offset / page_size) + 1

    query = (PaymentRequest
        .select(
            PaymentRequest,
            peewee.fn.SUM(PaymentRequestOutput.amount).alias("amount"))
        .join(PaymentRequestOutput)
        .group_by(PaymentRequest.uid))

    if filter_text is not None:
        filter_data = json.loads(filter_text)
        for filter_key, filter_values in filter_data.items():
            if len(filter_values):
                if filter_key == "state":
                    query = query.orwhere(PaymentRequest.state == filter_values)
                else:
                    log.error("get_invoices with unknown filter key: %s", filter_key)

    sort_key = PaymentRequest.date_created
    if sort_column == "creationTimestamp":
        sort_key = PaymentRequest.date_created
    elif sort_column == "expirationTimestamp":
        sort_key = PaymentRequest.date_expires
    elif sort_column == "description":
        sort_key = PaymentRequest.description
    elif sort_column == "state":
        sort_key = PaymentRequest.state
    elif sort_column == "amount":
        sort_key = PaymentRequestOutput.amount

    if sort_order == "desc":
        sort_key = -sort_key

    query = query.order_by(sort_key)

    results = query.paginate(current_page, page_size).objects()
    result_count = query.count() # pylint: disable=no-value-for-parameter

    data = {
        "total": result_count,
        "totalNotFiltered": result_count,
        "rows": [
            {
                "id": r.uid.hex,
                "state": r.state,
                "creationTimestamp": calendar.timegm(r.date_created.utctimetuple()),
                "expirationTimestamp":
                    calendar.timegm(r.date_expires.utctimetuple()) if r.date_expires else None,
                "description": r.description,
                "amount": r.amount,
                "tx_hash": r.tx_hash.hex() if r.tx_hash else None,
            } for r in results
        ],
    }

    return Response.json(data)

async def websocket_events(app: Application, request: Request, websocket: websockets.Websocket) \
        -> None:
    app.register_listener(websocket)
    while not websocket.closed:
        # Discard any incoming messages.
        msg = await websocket.recv()
    app.unregister_listener(websocket)
