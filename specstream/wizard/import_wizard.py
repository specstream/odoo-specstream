import urllib.parse

from odoo import _, fields, models

from .client import api_key, call

NAME_KEYS = ("company_name", "company", "name", "title", "organization")
SKIP_SUFFIX = "_source"


def lead_values(row):
    name = next((str(row[k]) for k in NAME_KEYS if row.get(k)), None) or _("SpecStream row")
    lines = []
    for field, value in row.items():
        if field.endswith(SKIP_SUFFIX) or value in (None, ""):
            continue
        source = row.get(field + SKIP_SUFFIX)
        lines.append("%s: %s%s" % (field, value, " (%s)" % source if source else ""))
    website = row.get("website") or row.get("domain") or ""
    return {
        "name": name,
        "website": website if isinstance(website, str) else "",
        "email_from": row.get("email") if isinstance(row.get("email"), str) else False,
        "phone": row.get("phone") if isinstance(row.get("phone"), str) else False,
        "description": "\n".join(lines),
    }


def create_leads(env, find_id, max_rows):
    """Create one CRM lead per row of a list. Reading rows costs nothing and starts no search."""
    key = api_key(env)
    find_id = urllib.parse.quote(find_id.strip(), safe="")
    rows, cursor = [], None
    while len(rows) < max_rows:
        query = {"limit": "100"}
        if cursor:
            query["cursor"] = cursor
        page = call("/v1/finds/%s/rows?%s" % (find_id, urllib.parse.urlencode(query)), key, timeout=30)
        rows += page.get("flat_rows") or []
        cursor = page.get("next_cursor")
        if not cursor:
            break
    leads = env["crm.lead"].create([lead_values(row) for row in rows[:max_rows]])
    return {
        "type": "ir.actions.act_window",
        "res_model": "crm.lead",
        "view_mode": "tree,form",
        "name": _("Leads from SpecStream"),
        "domain": [("id", "in", leads.ids)],
    }


class SpecstreamImportWizard(models.TransientModel):
    _name = "specstream.import.wizard"
    _description = "Import SpecStream rows as CRM leads"

    find_id = fields.Char(string="List id", required=True)
    max_rows = fields.Integer(string="Maximum rows", default=200)

    def action_import(self):
        self.ensure_one()
        return create_leads(self.env, self.find_id, self.max_rows)

    def _lead_values(self, row):
        """Watched lists build their leads with the same fields as an import."""
        return lead_values(row)
