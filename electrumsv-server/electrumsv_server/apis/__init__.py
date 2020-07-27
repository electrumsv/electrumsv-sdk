from functools import partial

from trinket import Trinket

from ..application import Application

from . import bip270


def add_api_routes(app: Application, server: Trinket) -> Trinket:
    server.route("/api/bip270")(
        partial(bip270.get_invoices, app))
    server.route("/api/bip270", ["POST"])(
        partial(bip270.create_invoice, app))
    server.route("/api/bip270/{id_text}/display")(
        partial(bip270.get_invoice_display_state, app))
    server.route("/api/bip270/{id_text}/cancel", ["POST"])(
        partial(bip270.cancel_invoice, app))
    server.route("/api/bip270/{id_text}")(
        partial(bip270.get_invoice, app))
    server.route("/api/bip270/{id_text}", ["POST"])(
        partial(bip270.submit_invoice_payment, app))

    server.websocket("/events")(
        partial(bip270.websocket_events, app))
    return server
