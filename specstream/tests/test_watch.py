from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.specstream.models import api as specstream_api

ROWS_V1 = [
    {"id": "f1:e1", "name": "Acme", "website": "https://acme.test", "website_source": "https://acme.test/about",
     "email": "hi@acme.test", "email_source": "https://acme.test/contact", "position": 1, "checked_at": "t1"},
    {"id": "f1:e2", "name": "Beta", "website": "https://beta.test", "email": "", "position": 2, "checked_at": "t1"},
]
ROWS_V2 = [
    {"id": "f2:e1", "name": "Acme", "website": "https://acme.test", "website_source": "https://acme.test/about",
     "email": "sales@acme.test", "email_source": "https://acme.test/team", "position": 1, "checked_at": "t2"},
    {"id": "f2:e3", "name": "Gamma", "website": "https://gamma.test", "position": 2, "checked_at": "t2"},
]


class FakeApi:
    def __init__(self):
        self.lists = {"f1": ROWS_V1}
        self.occurrences = []
        self.calls = []
        self.missing = set()

    def __call__(self, path, key, body=None, method=None):
        self.calls.append((method or ("POST" if body is not None else "GET"), path))
        if path.startswith("/v1/finds/"):
            find_id = path.split("/")[3]
            if find_id in self.missing:
                raise UserError("SpecStream returned error 404. Check the API key and the ids.")
            return {"status": "completed", "flat_rows": self.lists[find_id], "next_cursor": None}
        if path.endswith("/occurrences?limit=20"):
            return {"occurrences": self.occurrences}
        if path.endswith("/run"):
            return {"schedule_id": "s1", "find_id": "f9", "started_at": "now"}
        raise AssertionError(path)


@tagged("post_install", "-at_install")
class TestWatch(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param("specstream.api_key", "test-key")
        self.api = FakeApi()
        patcher = patch.object(specstream_api, "call", self.api)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _watch(self, **values):
        return self.env["specstream.watch"].create({"name": "Prospects", "find_id": "f1", **values})

    def test_first_check_creates_leads_with_sources(self):
        watch = self._watch()
        watch.action_check_now()
        self.assertEqual(len(watch.lead_ids), 2)
        acme = watch.lead_ids.filtered(lambda lead: lead.name == "Acme")
        self.assertEqual(acme.email_from, "hi@acme.test")
        self.assertIn("https://acme.test/contact", acme.description)
        self.assertEqual(set(watch.change_ids.mapped("kind")), {"new"})
        self.assertEqual(watch.last_find_id, "f1")

    def test_schedule_rerun_feeds_changes_and_updates_leads(self):
        watch = self._watch(schedule_id="s1")
        watch.action_check_now()
        self.api.lists["f2"] = ROWS_V2
        self.api.occurrences = [
            {"due_at": "2026-11-12T10:00:00+00:00", "status": "started", "find_id": "f3"},
            {"due_at": "2026-11-11T10:00:00+00:00", "status": "completed", "find_id": "f2"},
        ]
        watch.change_ids.unlink()
        watch.action_check_now()
        self.assertEqual(watch.last_find_id, "f2")
        changes = {(c.kind, c.row_name, c.field or ""): c for c in watch.change_ids}
        self.assertEqual(
            set(changes),
            {("changed", "Acme", "email"), ("new", "Gamma", ""), ("gone", "Beta", "")},
        )
        email = changes[("changed", "Acme", "email")]
        self.assertEqual((email.old_value, email.new_value), ("hi@acme.test", "sales@acme.test"))
        self.assertEqual(email.source, "https://acme.test/team")
        self.assertEqual(email.lead_id.email_from, "sales@acme.test")
        self.assertEqual(len(watch.lead_ids), 3)

    def test_unchanged_list_gives_no_changes(self):
        watch = self._watch()
        watch.action_check_now()
        count = len(watch.change_ids)
        self.assertEqual(watch._check(), 0)
        self.assertEqual(len(watch.change_ids), count)

    def test_unfinished_list_keeps_snapshot(self):
        watch = self._watch()
        with patch.object(specstream_api, "list_rows", return_value=([], "running")):
            watch.action_check_now()
        self.assertEqual(watch.snapshot, "{}")
        self.assertFalse(watch.change_ids)
        self.assertIn("running", watch.last_status)

    def test_cron_checks_due_watches_and_moves_them_on(self):
        now = fields.Datetime.now()
        due = self._watch(next_check=now - timedelta(minutes=1))
        later = self._watch(name="Later", next_check=now + timedelta(days=1))
        self.assertEqual(self.env["specstream.watch"]._cron_check_due(), 1)
        self.assertTrue(due.lead_ids)
        self.assertFalse(later.lead_ids)
        self.assertGreater(due.next_check, now + timedelta(hours=23))

    def test_cron_keeps_going_after_a_failing_watch(self):
        now = fields.Datetime.now()
        broken = self._watch(name="Broken", find_id="missing", next_check=now - timedelta(minutes=2))
        good = self._watch(next_check=now - timedelta(minutes=1))
        self.api.missing.add("missing")
        self.env["specstream.watch"]._cron_check_due()
        self.assertIn("404", broken.last_status)
        self.assertTrue(good.lead_ids)
        self.assertGreater(broken.next_check, now)

    def test_run_schedule_now_posts_to_the_schedule(self):
        watch = self._watch(schedule_id="s1")
        watch.action_run_schedule()
        self.assertIn(("POST", "/v1/capacity/schedules/s1/run"), self.api.calls)
        self.assertIn("f9", watch.last_status)
