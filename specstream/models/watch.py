import json
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from . import api as specstream

STEP = {"hour": relativedelta(hours=1), "day": relativedelta(days=1), "week": relativedelta(weeks=1)}
FINISHED = ("completed", "partial")
# Fields of a row that describe the list or the read, not the result itself.
NOT_VALUES = {"id", "list_id", "list_link", "position", "summary", "checked_at", "source_url", "not_confirmed"}
NAME_KEYS = ("name", "company_name", "company", "title", "organization")
MAX_DUE_PER_RUN = 20


def row_key(row):
    """The same result keeps its key in every read of the list and in every refresh of it."""
    flat_id = str(row.get("id") or "")
    entity = flat_id.partition(":")[2]
    if entity:
        return entity
    for field in ("website", "domain", "name"):
        if isinstance(row.get(field), str) and row[field].strip():
            return "%s:%s" % (field, row[field].strip().lower())
    return ""


def row_values(row):
    return {
        field: "" if value is None else str(value)
        for field, value in row.items()
        if field not in NOT_VALUES and not field.endswith("_source")
    }


def diff_rows(before, rows):
    """Compares one read of a list with the values kept from the read before it.

    Returns the new snapshot and the changes: a new result, a value that changed, a result that
    is no longer in the list.
    """
    after, changes = {}, []
    for row in rows:
        key = row_key(row)
        if not key or key in after:
            continue
        values = row_values(row)
        after[key] = values
        old = before.get(key)
        if old is None:
            changes.append({"row_key": key, "kind": "new", "row": row})
            continue
        for field, value in values.items():
            if old.get(field, "") != value:
                changes.append({
                    "row_key": key, "kind": "changed", "field": field, "row": row,
                    "old_value": old.get(field, ""), "new_value": value,
                    "source": str(row.get(field + "_source") or ""),
                })
    for key, old in before.items():
        if key not in after:
            changes.append({"row_key": key, "kind": "gone", "row": old})
    return after, changes


class CrmLead(models.Model):
    _inherit = "crm.lead"

    specstream_key = fields.Char(string="SpecStream result", index=True, copy=False, readonly=True)
    specstream_watch_id = fields.Many2one("specstream.watch", string="SpecStream watch", copy=False, readonly=True)


class SpecstreamWatch(models.Model):
    _name = "specstream.watch"
    _description = "SpecStream list read again on a schedule"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    find_id = fields.Char(string="List id", required=True, help="The id of a SpecStream list.")
    schedule_id = fields.Char(
        string="SpecStream schedule id",
        help="Optional. The id of a schedule you approved in SpecStream, with its spending limits. "
        "Each check reads the newest list that schedule finished. Leave it empty to read the same list again.",
    )
    interval = fields.Selection(
        [("hour", "Every hour"), ("day", "Every day"), ("week", "Every week")],
        string="Check", default="day", required=True,
    )
    max_rows = fields.Integer(string="Maximum rows", default=500)
    create_leads = fields.Boolean(string="Create and update leads", default=True)
    next_check = fields.Datetime(default=fields.Datetime.now, required=True)
    last_check = fields.Datetime(readonly=True)
    last_status = fields.Char(readonly=True)
    last_find_id = fields.Char(string="List read last", readonly=True)
    snapshot = fields.Text(readonly=True, copy=False, default="{}")
    change_ids = fields.One2many("specstream.change", "watch_id", string="Changes", readonly=True)
    change_count = fields.Integer(compute="_compute_change_count")
    lead_ids = fields.One2many("crm.lead", "specstream_watch_id", string="Leads", readonly=True)

    @api.depends("change_ids")
    def _compute_change_count(self):
        for watch in self:
            watch.change_count = len(watch.change_ids)

    def _current_find(self, key):
        if not self.schedule_id:
            return self.find_id.strip()
        page = specstream.call(
            "/v1/capacity/schedules/%s/occurrences?limit=20" % specstream.quote(self.schedule_id), key
        )
        for occurrence in page.get("occurrences") or []:
            if occurrence.get("status") == "completed" and occurrence.get("find_id"):
                return occurrence["find_id"]
        return self.last_find_id or self.find_id.strip()

    def _check(self):
        self.ensure_one()
        key = specstream.api_key(self.env)
        find_id = self._current_find(key)
        rows, status = specstream.list_rows(key, find_id, max(1, self.max_rows))
        now = fields.Datetime.now()
        if status and status not in FINISHED:
            self.write({"last_check": now, "last_status": _("List %s is %s. Read again at the next check.", find_id, status)})
            return 0
        before = json.loads(self.snapshot or "{}")
        after, changes = diff_rows(before, rows)
        leads = self._leads_by_key()
        records = []
        for change in changes:
            lead = leads.get(change["row_key"])
            if self.create_leads and change["kind"] != "gone":
                lead = self._save_lead(lead, change["row"], change["row_key"])
                leads[change["row_key"]] = lead
            records.append({
                "watch_id": self.id,
                "lead_id": lead.id if lead else False,
                "find_id": find_id,
                "row_key": change["row_key"],
                "row_name": _row_name(change["row"]),
                "kind": change["kind"],
                "field": change.get("field") or False,
                "old_value": change.get("old_value") or False,
                "new_value": change.get("new_value") or False,
                "source": change.get("source") or False,
            })
        self.env["specstream.change"].create(records)
        self.write({
            "snapshot": json.dumps(after),
            "last_check": now,
            "last_find_id": find_id,
            "last_status": _("%s results read, %s changes.", len(after), len(records)),
        })
        return len(records)

    def _leads_by_key(self):
        leads = self.env["crm.lead"].with_context(active_test=False).search([("specstream_watch_id", "=", self.id)])
        return {lead.specstream_key: lead for lead in leads if lead.specstream_key}

    def _save_lead(self, lead, row, key):
        values = self.env["specstream.import.wizard"]._lead_values(row)
        if lead:
            lead.write({k: v for k, v in values.items() if v})
            return lead
        values.update({"specstream_key": key, "specstream_watch_id": self.id})
        return self.env["crm.lead"].create(values)

    def action_check_now(self):
        for watch in self:
            watch._check()
        return True

    def action_run_schedule(self):
        """Starts one run of the SpecStream schedule now, inside the limits approved for it there."""
        self.ensure_one()
        if not self.schedule_id:
            raise UserError(_("Add the id of a SpecStream schedule first."))
        reply = specstream.call(
            "/v1/capacity/schedules/%s/run" % specstream.quote(self.schedule_id),
            specstream.api_key(self.env), body={}, method="POST",
        )
        self.last_status = _("Run started: list %s. Its changes come in at the next check.", reply.get("find_id") or "")
        return True

    def action_view_changes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "specstream.change",
            "view_mode": "tree,form",
            "name": _("Changes"),
            "domain": [("watch_id", "=", self.id)],
        }

    @api.model
    def _cron_check_due(self):
        now = fields.Datetime.now()
        due = self.search([("next_check", "<=", now)], limit=MAX_DUE_PER_RUN, order="next_check")
        for watch in due:
            try:
                with self.env.cr.savepoint():
                    watch._check()
            except UserError as error:
                watch.last_status = str(error.args[0] if error.args else error)
            step = STEP.get(watch.interval, STEP["day"])
            watch.next_check = max(watch.next_check + step, now + step - timedelta(minutes=5))
        return len(due)


def _row_name(row):
    return next((str(row[k]) for k in NAME_KEYS if row.get(k)), "") or str(row.get("id") or "")


class SpecstreamChange(models.Model):
    _name = "specstream.change"
    _description = "A change SpecStream found in a list"
    _order = "create_date desc, id desc"
    _rec_name = "row_name"

    watch_id = fields.Many2one("specstream.watch", required=True, ondelete="cascade", index=True)
    lead_id = fields.Many2one("crm.lead", ondelete="set null")
    find_id = fields.Char(string="List id")
    row_key = fields.Char(string="Result", index=True)
    row_name = fields.Char(string="Name")
    kind = fields.Selection(
        [("new", "New result"), ("changed", "Value changed"), ("gone", "No longer in the list")],
        required=True,
    )
    field = fields.Char()
    old_value = fields.Text(string="Before")
    new_value = fields.Text(string="Now")
    source = fields.Char(string="Source URL")
