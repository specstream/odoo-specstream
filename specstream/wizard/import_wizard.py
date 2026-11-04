import json
import urllib.error
import urllib.parse
import urllib.request

from odoo import _, fields, models
from odoo.exceptions import UserError

API = "https://api.specstream.ai"
NAME_KEYS = ("company_name", "company", "name", "title", "organization")
SKIP_SUFFIX = "_source"


def _get(path, key):
    request = urllib.request.Request(
        API + path,
        headers={"Authorization": "Bearer " + key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        raise UserError(_("SpecStream returned error %s. Check the API key and the list id.", error.code))
    except (urllib.error.URLError, TimeoutError):
        raise UserError(_("Couldn't reach SpecStream. Check the connection and try again."))
    except ValueError:
        raise UserError(_("Couldn't read the response from SpecStream. Try again in a moment."))
    return payload.get("data", payload)


class SpecstreamImportWizard(models.TransientModel):
    _name = "specstream.import.wizard"
    _description = "Import SpecStream rows as CRM leads"

    find_id = fields.Char(string="List id", required=True)
    max_rows = fields.Integer(string="Maximum rows", default=200)

    def action_import(self):
        self.ensure_one()
        key = self.env["ir.config_parameter"].sudo().get_param("specstream.api_key")
        if not key:
            raise UserError(_("Add your SpecStream API key in Settings > SpecStream first."))
        find_id = urllib.parse.quote(self.find_id.strip(), safe="")
        rows, cursor = [], None
        while len(rows) < self.max_rows:
            query = {"limit": "100"}
            if cursor:
                query["cursor"] = cursor
            page = _get("/v1/finds/%s/rows?%s" % (find_id, urllib.parse.urlencode(query)), key)
            rows += page.get("flat_rows") or []
            cursor = page.get("next_cursor")
            if not cursor:
                break
        leads = self.env["crm.lead"].create(
            [self._lead_values(row) for row in rows[: self.max_rows]]
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "view_mode": "tree,form",
            "name": _("Leads from SpecStream"),
            "domain": [("id", "in", leads.ids)],
        }

    def _lead_values(self, row):
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
