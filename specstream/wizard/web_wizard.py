import json
import urllib.error
import urllib.parse
import urllib.request

from odoo import _, fields, models
from odoo.exceptions import UserError

API = "https://api.specstream.ai"


def _call(path, key, body=None):
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        raise UserError(_("SpecStream returned error %s. Check the API key and the request.", error.code))
    except (urllib.error.URLError, TimeoutError):
        raise UserError(_("Couldn't reach SpecStream. Check the connection and try again."))
    except ValueError:
        raise UserError(_("Couldn't read the response from SpecStream. Try again in a moment."))
    return payload.get("data", payload)


def _key(env):
    key = env["ir.config_parameter"].sudo().get_param("specstream.api_key")
    if not key:
        raise UserError(_("Add your SpecStream API key in Settings > SpecStream first."))
    return key


class SpecstreamSearchWizard(models.TransientModel):
    _name = "specstream.search.wizard"
    _description = "Search the web with SpecStream"

    query = fields.Char(string="Question", required=True, help="1 to 2,000 characters, in everyday words.")
    result = fields.Text(string="Answer and sources", readonly=True)

    def action_search(self):
        self.ensure_one()
        q = (self.query or "").strip()
        if not q or len(q) > 2000:
            raise UserError(_("Enter a question between 1 and 2,000 characters."))
        reply = _call("/v1/web-search?" + urllib.parse.urlencode({"q": q}), _key(self.env))
        lines = []
        answer = reply.get("answer")
        if isinstance(answer, dict) and answer.get("value"):
            lines.append("%s: %s" % (_("Answer"), answer["value"]))
            if answer.get("page"):
                lines.append("%s: %s" % (_("Read from"), answer["page"]))
            lines.append("")
        for source in reply.get("sources") or []:
            lines.append("%s - %s" % (source.get("title") or source.get("site") or "", source.get("url") or ""))
        self.result = "\n".join(lines) or _("No results.")
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }


class SpecstreamExtractWizard(models.TransientModel):
    _name = "specstream.extract.wizard"
    _description = "Extract web pages with SpecStream"

    urls = fields.Text(string="URLs", required=True, help="1 to 20 http or https URLs, one per line.")
    output_format = fields.Selection(
        [("markdown", "Markdown"), ("text", "Plain text")], string="Format", default="markdown", required=True
    )
    result = fields.Text(string="Page text", readonly=True)

    def action_extract(self):
        self.ensure_one()
        urls = [u.strip() for u in (self.urls or "").replace(",", "\n").splitlines() if u.strip()]
        if not urls or len(urls) > 20:
            raise UserError(_("Enter 1 to 20 http or https URLs."))
        reply = _call("/v1/extract", _key(self.env), {"urls": urls, "format": self.output_format})
        blocks = []
        for item in reply.get("results") or []:
            head = "%s [%s]" % (item.get("url") or "", item.get("status") or "")
            blocks.append("%s\n%s" % (head, item.get("text") or ""))
        self.result = "\n\n".join(blocks) or _("No results.")
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
