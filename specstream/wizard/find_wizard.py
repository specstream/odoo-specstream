import urllib.parse

from odoo import _, fields, models
from odoo.exceptions import UserError

from .client import api_key, call
from .import_wizard import create_leads

MAX_REQUEST_CHARS = 2000


def _dollars(cents, currency):
    symbol = "$" if currency == "USD" else currency + " "
    return "%s%.2f" % (symbol, cents / 100)


class SpecstreamFindWizard(models.TransientModel):
    """Find rows: read a request, show its maximum price, and start it only after the user approves."""

    _name = "specstream.find.wizard"
    _description = "Find rows with SpecStream"

    request = fields.Text(string="Request", required=True, help="What to find, in everyday words.")
    count = fields.Integer(string="Number of rows", default=25, required=True)
    state = fields.Selection(
        [("draft", "Request"), ("quoted", "Price"), ("started", "Started")],
        default="draft",
        required=True,
    )
    read_as = fields.Text(string="SpecStream read it as", readonly=True)
    price = fields.Char(string="Maximum price", readonly=True)
    quote_id = fields.Char(readonly=True)
    quote_hash = fields.Char(readonly=True)
    maximum_cents = fields.Integer(readonly=True)
    find_id = fields.Char(string="List id", readonly=True)
    status = fields.Char(string="Status", readonly=True)
    max_rows = fields.Integer(string="Maximum leads", default=200)

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_quote(self):
        """Read the request and price it. This spends nothing."""
        self.ensure_one()
        text = " ".join((self.request or "").split())
        if not text or len(text) > MAX_REQUEST_CHARS:
            raise UserError(_("Write a request between 1 and 2,000 characters."))
        if not 1 <= self.count <= 10000:
            raise UserError(_("Ask for 1 to 10,000 rows."))
        key = api_key(self.env)
        reading = call("/v1/parse", key, {"q": text, "locale": "en-US"})
        ast_hash = reading.get("ast_hash")
        if reading.get("status") != "runnable" or not isinstance(ast_hash, str):
            raise UserError(
                _(
                    "SpecStream needs a clearer request. Name what to find and where, "
                    "like \"roofing companies in Columbus, Ohio with their phone\"."
                )
            )
        quote = call(
            "/v1/capacity/quotes",
            key,
            {"ast_hash": ast_hash, "operation": "find", "requested_units": self.count},
        )
        cents = quote.get("maximum_cents")
        if not quote.get("quote_id") or not quote.get("quote_hash") or not isinstance(cents, int):
            raise UserError(_("SpecStream couldn't price that request. Try again in a moment."))
        most = _dollars(cents, str(quote.get("currency") or "USD"))
        self.write(
            {
                "state": "quoted",
                "read_as": reading.get("read_back") or reading.get("canonical_sentence") or text,
                "price": _("Up to %s. You pay only for the rows delivered.", most),
                "quote_id": quote["quote_id"],
                "quote_hash": quote["quote_hash"],
                "maximum_cents": cents,
            }
        )
        return self._reopen()

    def action_start(self):
        """Approve the quoted maximum and start the list. The key makes a second click start nothing new."""
        self.ensure_one()
        if self.state != "quoted" or not self.quote_id:
            raise UserError(_("Get the price first."))
        started = call(
            "/v1/capacity/executions",
            api_key(self.env),
            {
                "quote_id": self.quote_id,
                "quote_hash": self.quote_hash,
                "idempotency_key": "odoo-" + self.quote_id,
                "confirm_max_cents": self.maximum_cents,
            },
        )
        find_id = started.get("find_id")
        if not find_id:
            raise UserError(_("SpecStream accepted the approval but hasn't started the list yet. Click again in a moment."))
        self.write({"state": "started", "find_id": find_id, "status": started.get("state") or "running"})
        return self._reopen()

    def action_refresh(self):
        self.ensure_one()
        if not self.find_id:
            raise UserError(_("Start the list first."))
        page = call(
            "/v1/finds/%s/rows?limit=1" % urllib.parse.quote(self.find_id, safe=""),
            api_key(self.env),
            timeout=30,
        )
        status = page.get("status") or ""
        rows = page.get("accepted_count") or 0
        self.status = _("%s, %s rows", status, rows) if status else _("%s rows", rows)
        return self._reopen()

    def action_create_leads(self):
        self.ensure_one()
        if not self.find_id:
            raise UserError(_("Start the list first."))
        return create_leads(self.env, self.find_id, self.max_rows)
