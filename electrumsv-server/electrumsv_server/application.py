import asyncio
import calendar
import datetime
import socket
import sys
import uuid
import logging
import mimetypes
from typing import Optional, Dict, Any, TypedDict, cast

import aiohttp
import bitcoinx
import peewee
from aiohttp import web, AsyncResolver
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from argparse import Namespace
import json
import os

from bitcoinx import PrivateKey

from .database import open_database, PaymentRequest, PaymentRequestOutput
from .exceptions import StartupError
from .constants import DEFAULT_PAGE, RequestState
from .config import parse_args, get_network_choice, get_mapi_uri, get_reference_server_uri
from .payment_requests import get_next_script
from .txstatewebsocket import TxStateWebSocket, WSClient
from .types import PeerChannelViewModelGet, PaymentDPP, HYBRID_PAYMENT_MODE_BRFCID, PeerChannel, \
    PaymentTermsDPP, PaymentACK

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Silence verbose logging
db_logger = logging.getLogger("peewee")
db_logger.setLevel(logging.WARNING)
aiohttp_logger = logging.getLogger("aiohttp")
aiohttp_logger.setLevel(logging.WARNING)


CLIENT_IDENTITY_PRIVATE_KEY_HEX = "d468816bc0f78465d4833426c280166c3810ecc9c0350c5232b0c417687fbde6"
CLIENT_IDENTITY_PRIVATE_KEY = PrivateKey.from_hex(CLIENT_IDENTITY_PRIVATE_KEY_HEX)

REFERENCE_SERVER_POST_ACCOUNT_KEY = "/api/v1/account/key"
REFERENCE_SERVER_CREATE_PEER_CHANNEL = "/api/v1/channel/manage"


class PeerChannelCreationError(Exception):
    pass

class VerifiableKeyData(TypedDict):
    public_key_hex: str
    signature_hex: str
    message_hex: str


def _generate_client_key_data() -> VerifiableKeyData:
    iso_date_text = datetime.datetime.utcnow().isoformat()
    message_bytes = b"http://server/api/account/metadata" + iso_date_text.encode()
    signature_bytes = CLIENT_IDENTITY_PRIVATE_KEY.sign_message(message_bytes)
    return {
        "public_key_hex": CLIENT_IDENTITY_PRIVATE_KEY.public_key.to_hex(),
        "message_hex": message_bytes.hex(),
        "signature_hex": signature_bytes.hex()
    }



class ApplicationState(object):

    def __init__(self, config: Namespace, web_app: web.Application) -> None:
        self.web_app = web_app
        self.web_app['ws_clients'] = {}  # uuid: WSClient
        self.web_app['tx_registrations_map'] = {}
        self.loop = asyncio.get_event_loop()
        self.config = config
        self.logger = logging.getLogger("application-state")
        self.mapi_uri = get_mapi_uri(self.config.network_choice)
        self.reference_server_uri = get_reference_server_uri(self.config.network_choice)

        wwwroot_path = self._validate_path(config.wwwroot_path)
        if not os.path.exists(os.path.join(wwwroot_path, "index.html")):
            raise StartupError(f"The wwwroot path '{wwwroot_path}' lacks an 'index.html' file.")
        self.wwwroot_path = wwwroot_path

        self.data_path = self._validate_path(config.data_path, create=True)

        self.db = open_database(self)
        self._listeners = []

        self.client_session: Optional[aiohttp.ClientSession]=None

    @staticmethod
    async def on_startup(app):
        app.app_state.client_session = await app.app_state._get_aiohttp_session()

    @staticmethod
    async def on_shutdown(app):
        await app.app_state._close_aiohttp_session()

    async def _get_aiohttp_session(self):
        # aiohttp session needs to be initialised in async function
        # https://github.com/tiangolo/fastapi/issues/301
        if self.client_session is None:
            resolver = AsyncResolver()
            conn = aiohttp.TCPConnector(family=socket.AF_INET, resolver=resolver, ttl_dns_cache=10,
                                        force_close=True, enable_cleanup_closed=True)
            self.client_session = aiohttp.ClientSession(connector=conn)
        return self.client_session

    async def _close_aiohttp_session(self):
        self.logger.debug("closing aiohttp client session.")
        if self.client_session:
            await self.client_session.close()

    async def _decode_response_body(self, response) -> Dict[Any, Any]:
        body = await response.read()
        if body == b"" or body == b"{}":
            return {}
        return json.loads(body.decode())

    def _validate_path(self, path: str, create: bool=False) -> str:
        path = os.path.realpath(path)
        if not os.path.exists(path):
            if not create:
                raise StartupError(f"The path '{path}' does not exist.")
            os.makedirs(path)
        return path

    def register_listener(self, ws) -> None:
        self._listeners.append(ws)

    def unregister_listener(self, ws) -> None:
        self._listeners.remove(ws)

    async def notify_listeners(self, value) -> None:
        text = json.dumps(value)
        for ws_client in self.web_app['ws_clients'].values():
            ws_client: WSClient
            await ws_client.websocket.send_str(text)

    # ----- WEBSITE ----- #

    async def serve_file(self, request: web.Request) -> Response:
        filepath = request.path[1:].split("/")
        try:
            if filepath == [""]:
                filepath = [DEFAULT_PAGE]
            page_path = os.path.realpath(os.path.join(self.wwwroot_path, *filepath))
            if not page_path.startswith(self.wwwroot_path) or not os.path.exists(page_path):
                print("..... filename %r", page_path)
                raise FileNotFoundError

            content_type, encoding_name = mimetypes.guess_type(filepath[-1])
            with open(page_path, 'rb') as f:
                content = f.read()
                return web.Response(body=content, content_type=content_type)

        except FileNotFoundError:
            return web.Response(body=f"<html>Page not found: {filepath}</html>", status=404)
        except Exception:
            self.logger.exception("Rendering page failed unexpectedly")
            return web.Response(status=500)

    # ----- API -----#

    async def create_invoice(self, request: web.Request) -> web.Response:
        data = await request.json()
        self.logger.debug(f"Creating invoice with request body: {data}")

        if type(data) is not dict:
            return web.Response(body="invalid payment data type", status=400)

        description = data.get("description")
        if description is not None:
            if type(description) is not str:
                return web.Response(body="invalid payment description type", status=400)
            if not description.strip():
                description = None

        output_list = data.get("outputs")
        if type(output_list) is not list:
            return web.Response(body="invalid payment outputs type", status=400)

        expiration_minutes = data.get("expiration")
        if type(expiration_minutes) is not int:
            return web.Response(body="invalid payment expiration value", status=400)

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
            database_outputs.append(
                PaymentRequestOutput(description=description, amount=amount, script=script,
                    request=request_uid))
            response_outputs.append({"description": description, "amount": amount})

        with self.db.atomic():
            PaymentRequest.bulk_create([request])
            PaymentRequestOutput.bulk_create(database_outputs, batch_size=100)

        return web.Response(body=json.dumps(request_uid.hex), status=200)

    async def _get_invoice(self, invoice_id: uuid.UUID,
            for_display: bool = False) -> PaymentTermsDPP:
        pr = (PaymentRequest.select(PaymentRequest, PaymentRequestOutput).join(
            PaymentRequestOutput).where(PaymentRequest.uid == invoice_id)).get()

        outputs_object = []
        for output in pr.outputs:
            outputs_object.append({"description": output.description, "amount": output.amount,
                "script": output.script.hex()})

        id_text = str(invoice_id)

        # This is now updated to adhere to the spec defined at:
        # https://tsc.bitcoinassociation.net/standards/direct_payment_protocol/#Specification
        merchant_data = json.dumps({
                "avatar": "https://thispersondoesnotexist.com/image",
                "name": "Epictetus",
                "email": "epic@nchain.com",
                "address": "1 Athens Avenue",
                "extendedData": {
                    "dislikes": "Malfeasance",
                    "likes": "Stoicism & placeholder data",
                    "paymentReference": "2V9yM33"
                }
        })

        paymentRequestData = {
            "network": "regtest",
            "version": "1.0",
            # "outputs": outputs_object,  # DEPRECATED in TSC Spec.
            "creationTimestamp": calendar.timegm(pr.date_created.utctimetuple()),
            "expirationTimestamp": calendar.timegm(
                pr.date_expires.utctimetuple()) if pr.date_expires else None,
            "paymentUrl": f"pay:?r=http://127.0.0.1:{self.config.http_server_port}"
                          f"/api/dpp/v1/payment/{id_text}&sv",
            "beneficiary": {
                "name": "GoldenSocks.com",
                "paymentReference": "Order-325214",
            },
            "memo": pr.description,
            "merchantData": merchant_data,

            # NOTE: The "outputs" field is dropped as it is deprecated in the TSC spec. but is
            # allowable only for backwards compatability.
            # ElectrumSV should reject invoices that use this deprecated "outputs" field IMO
            # as it is tech debt we could do without at this early stage. - AustEcon

            # Hybrid Payment Mode
            'modes': {
                'ef63d9775da5': {
                    "choiceID0": {
                        "transactions": [
                            {
                                'outputs': {
                                    'native': outputs_object,
                                },
                                'policies': {
                                    'fees': {
                                        'standard': {
                                            "satoshis": 100,
                                            "bytes": 200
                                        },
                                        'data': {
                                            'satoshis': 100,
                                            'bytes': 200
                                        }
                                    },
                                    'SPVRequired': False
                                }
                            },
                        ],
                    },
                }
            }
        }

        if for_display:
            paymentRequestData["id"] = id_text
            paymentRequestData["state"] = pr.state
            paymentRequestData["outputs"] = outputs_object
        return cast(PaymentTermsDPP, paymentRequestData)

    async def get_invoice(self, request: Request) -> Response:
        id_text = request.match_info['id_text']
        request_id = uuid.UUID(hex=id_text)
        result = await self._get_invoice(request_id)
        return web.Response(body=json.dumps(result), headers={'Content-Type': 'application/json'},
            status=200)

    async def get_invoice_display_state(self, request: Request) -> Response:
        id_text = request.match_info['id_text']
        request_id = uuid.UUID(hex=id_text)
        result = {"paymentRequest": await self._get_invoice(request_id, for_display=True),
            "paymentUri": f"pay:?r=http://127.0.0.1:"
                          f"{self.config.http_server_port}/api/dpp/v1/payment/{id_text}&sv", }
        return web.Response(body=json.dumps(result), status=200)

    async def cancel_invoice(self, request: Request) -> Response:
        id_text = request.match_info['id_text']
        request_id = uuid.UUID(hex=id_text)

        # Mark the invoice as paid by the given transaction.
        query = (PaymentRequest.update({PaymentRequest.state: RequestState.CLOSED, }).where(
            PaymentRequest.uid == request_id.bytes))
        query.execute()
        return web.Response(body=json.dumps(True), status=200)

    async def submit_invoice_payment(self, request: Request) -> Response:
        id_text = request.match_info['id_text']
        payment_object = cast(PaymentDPP, await self._decode_response_body(request))
        self.logger.debug(f"Invoice payment submitted with request body: {payment_object}")

        content_type = request.headers.get('Content-Type')
        if content_type != "application/bitcoinsv-payment":
            return web.Response(body=content_type, status=web.HTTPUnsupportedMediaType.status_code)

        accept_content_type = request.headers.get('Accept')
        if accept_content_type != "application/bitcoinsv-paymentack":
            return web.Response(body=accept_content_type, status=web.HTTPNotAcceptable.status_code)

        request_id = uuid.UUID(hex=id_text)
        pr = (PaymentRequest.select(PaymentRequest, PaymentRequestOutput).join(
            PaymentRequestOutput).where(PaymentRequest.uid == request_id.bytes)).get()

        # Verify that the transaction is complete.
        if type(payment_object) is not dict:
            return web.Response(body="invalid payment object", status=400)

        if "modeId" not in payment_object:
            return web.Response(body="payment object lacks modeId", status=400)

        if "mode" not in payment_object:
            return web.Response(body="payment object lacks mode", status=400)

        transactions = payment_object['mode'][HYBRID_PAYMENT_MODE_BRFCID]['transactions']
        if len(transactions) > 1:
            return web.Response(body="payment object contains more than one transaction."
                                     "We can only handle a single transaction at present",
                status=400)

        try:
            tx = bitcoinx.Tx.from_hex(transactions[0])
        except (TypeError, ValueError):
            # TypeError: from_hex gets non string.
            # ValueError: from_hex gets invalid hex encoded data.
            return web.Response(body="Invoice has an invalid payment transaction", status=400)

        if pr.tx_hash is None:
            self.logger.debug("Attempting to settle payment request with tx '%s'", tx.hex_hash())

            # Verify that the outputs are present.
            tx_outputs = {bytes(out.script_pubkey): out.value for out in tx.outputs}
            try:
                for output in pr.outputs:
                    if output.amount != tx_outputs[output.script]:
                        return web.Response(body="Invoice has an invalid output amount",
                            status=400)
            except KeyError:
                return web.Response(body="Invoice has a missing output", status=400)

            # Broadcast via Merchant API

            self.client_session: aiohttp.ClientSession

            # Create a Peer Channel for the mAPI callback
            # 1) Get api key (Bearer Token) for Peer Channel Creation
            key_data = _generate_client_key_data()
            url = self.reference_server_uri + REFERENCE_SERVER_POST_ACCOUNT_KEY
            api_key = None
            async with self.client_session.post(url, data=json.dumps(key_data)) as resp:
                reader = aiohttp.MultipartReader.from_response(resp)
                while True:
                    part = await reader.next()
                    if part is None:
                        break

                    if part.name == 'api-key':
                        api_key = await part.text()

            if api_key is None:
                raise PeerChannelCreationError("Failed to get reference server API key")

            # 2) Create Peer Channel
            url = self.reference_server_uri + REFERENCE_SERVER_CREATE_PEER_CHANNEL
            headers = {'Content-Type': 'application/json',
                       'Authorization': f'Bearer {api_key}'}
            body = {
              "public_read": True,
              "public_write": True,
              "sequenced": True,
              "retention": {
                "min_age_days": 0,
                "max_age_days": 0,
                "auto_prune": True
              }
            }
            async with self.client_session.post(url, headers=headers,
                    data=json.dumps(body)) as resp:
                if resp.status != 200:
                    raise PeerChannelCreationError(resp.reason)

                peer_channel_json = cast(PeerChannelViewModelGet,
                    await self._decode_response_body(resp))

                self.logger.debug(f"Created new peer channel with details: {peer_channel_json}")


            # Broadcasting the transaction verifies that the transaction is valid.
            mapi_uri = f"{self.mapi_uri}/tx"
            payload = {
                "rawtx": tx.to_hex(),
                "merkleProof": False,
                "dsCheck": False,
                "callbackUrl": peer_channel_json["href"],
            }
            headers = {'Content-Type': 'application/json'}

            async with self.client_session.post(mapi_uri, headers=headers,
                    data=json.dumps(payload), ssl=False) as resp:

                json_response = await self._decode_response_body(resp)
                if resp.status != 200:
                    self.logger.error(f"broadcast failed with: {json_response}")
                    return web.Response(body="broadcast failed", status=400)
                assert json_response['encoding'].lower() == 'utf-8'
                json_payload = json.loads(json_response['payload'])
                self.logger.debug(f"successful broadcast for {json_payload['txid']}")

            # Mark the invoice as paid by the given transaction.
            query = (PaymentRequest.update({PaymentRequest.tx_hash: tx.hash(),
                PaymentRequest.state: RequestState.PAID, }).where(
                PaymentRequest.uid == request_id.bytes))
            query.execute()

            self.logger.debug("Payment request '%s' paid with tx '%s'", request_id, tx.hex_hash())
            await self.notify_listeners(
                ["InvoicePaid", id_text])  # TODO: Notify any connected listener.
        elif pr.tx_hash != tx.hash():
            return web.Response(body="Invoice already paid with different payment", status=400)

        # DPP PaymentACK object - see DPP TSC spec.
        ack_object = cast(PaymentACK, {
            "modeId": payment_object['modeId'],
            "mode": payment_object['mode'],
            "peerChannel": PeerChannel(host=self.reference_server_uri,
                token=peer_channel_json['access_tokens'][0]['token'],
                channelid=peer_channel_json['id'])

        })
        self.logger.debug(f"PaymentACK response: {ack_object}")
        return web.Response(body=json.dumps(ack_object), headers={'Content-Type':
            'application/bitcoinsv-paymentack', }, status=200)

    async def get_invoices(self, request: Request) -> Response:
        sort_order = request.query.get('order', "desc")
        offset = int(request.query.get('offset'))
        page_size = int(request.query.get('limit'))
        sort_column = request.query.get('sort', "creationTimestamp")
        filter_text = request.query.get('filter', None)

        current_page = (offset / page_size) + 1

        query = (PaymentRequest.select(PaymentRequest,
            peewee.fn.SUM(PaymentRequestOutput.amount).alias("amount")).join(
            PaymentRequestOutput).group_by(PaymentRequest.uid))

        if filter_text is not None:
            filter_data = json.loads(filter_text)
            for filter_key, filter_values in filter_data.items():
                if len(filter_values):
                    if filter_key == "state":
                        query = query.orwhere(PaymentRequest.state == filter_values)
                    else:
                        self.logger.error("get_invoices with unknown filter key: %s", filter_key)

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
        result_count = query.count()  # pylint: disable=no-value-for-parameter

        data = {"total": result_count, "totalNotFiltered": result_count, "rows": [
            {"id": r.uid.hex, "state": r.state,
                "creationTimestamp": calendar.timegm(r.date_created.utctimetuple()),
                "expirationTimestamp": calendar.timegm(
                    r.date_expires.utctimetuple()) if r.date_expires else None,
                "description": r.description, "amount": r.amount,
                "tx_hash": r.tx_hash.hex() if r.tx_hash else None, } for r in results], }

        self.logger.debug(f"application: get_invoices data: {data}")
        return web.Response(body=json.dumps(data), status=200)


def add_website_routes(web_app: web.Application, app_state: ApplicationState):
    """static from wwwroot dir"""
    web_app.add_routes([web.get("/", app_state.serve_file)])  # Index
    web_paths = []
    for root_path, dirnames, filenames in os.walk(app_state.wwwroot_path):
        if len(filenames):
            web_path = os.path.relpath(root_path, app_state.wwwroot_path).replace(
                os.path.sep, "/")
            web_paths.append(web_path)

    # Deeper paths need to be routed first so as to not override shallower paths.
    for web_path in sorted(web_paths, key=len, reverse=True):
        if web_path == ".":
            web_app.add_routes([web.get("/{filename}", app_state.serve_file), ])
        else:
            web_app.add_routes(
                [web.get("/" + web_path + "/{filename}", app_state.serve_file), ])
    return web_app


def add_api_routes(web_app: web.Application, app_state: ApplicationState):
    web_app.add_routes([
        web.get("/api/dpp", app_state.get_invoices),
        web.post("/api/dpp", app_state.create_invoice),
        web.get("/api/dpp/{id_text}/display", app_state.get_invoice_display_state),
        web.post("/api/dpp/{id_text}/cancel", app_state.cancel_invoice),
        web.get("/api/dpp/v1/payment/{id_text}", app_state.get_invoice),
        web.post("/api/dpp/v1/payment/{id_text}", app_state.submit_invoice_payment),
    ])
    return web_app


def add_websocket_route(web_app: web.Application, app_state: ApplicationState):
    web_app.add_routes([
        web.view("/websocket/text-events", TxStateWebSocket),
    ])
    return web_app


async def init():
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(name)-24s %(message)s',
        level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

    config = parse_args()
    config.network_choice = get_network_choice(config)
    web_app = web.Application()
    app_state = ApplicationState(config, web_app)
    web_app.app_state = app_state

    # routes
    web_app = add_website_routes(web_app, app_state)
    web_app = add_api_routes(web_app, app_state)
    web_app = add_websocket_route(web_app, app_state)

    web_app.on_startup.append(app_state.on_startup)
    web_app.on_shutdown.append(app_state.on_shutdown)
    return web_app


def run() -> None:
    try:
        web.run_app(init(), host="127.0.0.1", port=24242)
    except StartupError as e:
        sys.exit(e)
