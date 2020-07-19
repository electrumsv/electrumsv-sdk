import calendar
import datetime
from functools import partial
import json
import os
from typing import Any, Dict, Optional
import uuid

from trinket import Request, Response, Trinket
from trinket.extensions import logger
from trinket.http import HTTPError, HTTPStatus

from .application import Application
from .constants import DEFAULT_PAGE
from .database import PaymentRequest, PaymentRequestOutput


async def api_home(app: Application, request: Request, filename: Optional[str]=None) -> Response:
    if not filename: filename = DEFAULT_PAGE
    page_path = os.path.realpath(os.path.join(app.wwwroot_path, filename))
    if not page_path.startswith(app.wwwroot_path) or not os.path.exists(page_path):
        raise HTTPError(HTTPStatus.NOT_FOUND, f"<html>Page not found: {filename}</html>")

    with open(page_path, "r") as f:
        return Response.html(f.read())

async def api_bip270_payment_prepare(app: Application, request: Request) -> Response:
    data = json.loads(await request.raw_body)

    request_uid = uuid.uuid4()
    description = "Payment required"
    date_created = datetime.datetime.utcnow()
    date_expires = date_created + datetime.timedelta(minutes=10)
    request = PaymentRequest(uid=request_uid, description=description,
        date_created=date_created, date_expires=date_expires)

    script = os.urandom(16) # TODO: FIX

    outputs = []
    for amount_entry in data:
        description, amount = amount_entry
        assert description is None or type(description) is str and len(description) < 100
        assert type(amount) is int
        outputs.append(PaymentRequestOutput(description=description, amount=amount,
            script=script, request=request_uid))

    with app.db.atomic():
        PaymentRequest.bulk_create([ request ])
        PaymentRequestOutput.bulk_create(outputs, batch_size=100)

    id_text = str(request_uid)
    response = {
        "request_uri": f"127.0.0.1:{app.config.http_server_port}/api/bip270/{id_text}",
        "expiry_timestamp": calendar.timegm(date_expires.utctimetuple()),
    }
    return Response.json(response)


async def api_bip270_payment_request(app: Application, request: Request, id_text: str) -> Response:
    request_id = uuid.UUID(hex=id_text)

    request = (PaymentRequest.select(PaymentRequest, PaymentRequestOutput)
        .join(PaymentRequestOutput)
        .where(PaymentRequest.uid == request_id.bytes)).get()

    outputs_object = []
    for output in request.outputs:
        outputs_object.append({ "description": output.description, "amount": output.amount,
            "script": output.script.hex()  })

    request_object = {
        "network": "bitcoin",
        "paymentUrl":
            f"127.0.0.1:{app.config.http_server_port}/api/bip270/{id_text}",
        "outputs": outputs_object,
        "creationTimestamp": calendar.timegm(request.date_created.utctimetuple()),
        "expirationTimestamp": calendar.timegm(request.date_expires.utctimetuple()),
    }
    return Response.json(request_object)


def create(app: Application) -> Trinket:
    server = logger(Trinket())
    server.route("/")(partial(api_home, app))
    server.route("/api/bip270", ["POST"])(
        partial(api_bip270_payment_prepare, app))
    server.route("/api/bip270/{id_text}")(
        partial(api_bip270_payment_request, app))
    server.route("/{filename}")(partial(api_home, app))
    return server

