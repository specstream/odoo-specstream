from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.specstream.wizard import find_wizard, import_wizard

QUOTE = {"quote_id": "q_1", "quote_hash": "h" * 64, "maximum_cents": 125, "currency": "USD"}


class FakeApi:
    def __init__(self):
        self.calls = []

    def __call__(self, path, key, body=None, timeout=None):
        self.calls.append((path, body))
        if path == "/v1/parse":
            return {"status": "runnable", "ast_hash": "a" * 64, "read_back": "Dentists in Austin, TX"}
        if path == "/v1/capacity/quotes":
            return dict(QUOTE)
        if path == "/v1/capacity/executions":
            return {"find_id": "f_1", "state": "reserved"}
        if path.startswith("/v1/finds/f_1/rows"):
            return {"status": "completed", "accepted_count": 1, "next_cursor": None,
                    "flat_rows": [{"name": "Smile Co", "phone": "+1 512", "phone_source": "https://smile.test"}]}
        raise AssertionError(path)


@tagged("post_install", "-at_install")
class TestFind(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param("specstream.api_key", "test-key")
        self.api = FakeApi()
        for module in (find_wizard, import_wizard):
            patcher = patch.object(module, "call", self.api)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_price_then_approve_starts_the_quoted_maximum_once(self):
        wizard = self.env["specstream.find.wizard"].create({"request": "dentists in Austin with their phone"})
        with self.assertRaises(UserError):
            wizard.action_start()
        wizard.action_quote()
        self.assertEqual(wizard.state, "quoted")
        self.assertIn("$1.25", wizard.price)
        self.assertEqual([path for path, _ in self.api.calls], ["/v1/parse", "/v1/capacity/quotes"])
        wizard.action_start()
        self.assertEqual(self.api.calls[-1][1], {"quote_id": "q_1", "quote_hash": "h" * 64,
                                                 "idempotency_key": "odoo-q_1", "confirm_max_cents": 125})
        self.assertEqual((wizard.state, wizard.find_id), ("started", "f_1"))

    def test_rows_of_the_started_list_become_leads_with_sources(self):
        wizard = self.env["specstream.find.wizard"].create(
            {"request": "dentists", "state": "started", "find_id": "f_1"})
        wizard.action_refresh()
        self.assertIn("1 rows", wizard.status)
        action = wizard.action_create_leads()
        lead = self.env["crm.lead"].browse(action["domain"][0][2])
        self.assertEqual(lead.name, "Smile Co")
        self.assertIn("phone: +1 512 (https://smile.test)", lead.description)
