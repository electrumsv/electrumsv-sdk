from functools import partial

from trinket import Trinket

from ..application import Application

from . import bip270


def add_api_routes(app: Application, server: Trinket) -> Trinket:
    server.route("/api/bip270", ["POST"])(
        partial(bip270.api_bip270_payment_prepare, app))
    server.route("/api/bip270/{id_text}")(
        partial(bip270.api_bip270_payment_request_get, app))
    server.route("/api/bip270/{id_text}", ["POST"])(
        partial(bip270.api_bip270_payment_request_post, app))
    return server
