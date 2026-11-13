import json
import urllib.error
import urllib.parse
import urllib.request

from odoo import _
from odoo.exceptions import UserError

API = "https://api.specstream.ai"


def api_key(env):
    key = env["ir.config_parameter"].sudo().get_param("specstream.api_key")
    if not key:
        raise UserError(_("Add your SpecStream API key in Settings > SpecStream first."))
    return key


def call(path, key, body=None, method=None):
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json", "User-Agent": "specstream-odoo/17.0.1.2.0"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as error:
        raise UserError(_("SpecStream returned error %s. Check the API key and the ids.", error.code))
    except (urllib.error.URLError, TimeoutError):
        raise UserError(_("Couldn't reach SpecStream. Check the connection and try again."))
    except ValueError:
        raise UserError(_("Couldn't read the response from SpecStream. Try again in a moment."))
    return payload.get("data", payload) if isinstance(payload, dict) else {}


def quote(value):
    return urllib.parse.quote((value or "").strip(), safe="")


def list_rows(key, find_id, max_rows):
    """Reads the rows of one list, page by page. Reading a list costs nothing."""
    rows, cursor, status = [], None, None
    while len(rows) < max_rows:
        query = {"limit": "100"}
        if cursor:
            query["cursor"] = cursor
        page = call("/v1/finds/%s/rows?%s" % (quote(find_id), urllib.parse.urlencode(query)), key)
        status = status or page.get("status")
        rows += page.get("flat_rows") or []
        cursor = page.get("next_cursor")
        if not cursor:
            break
    return rows[:max_rows], status
