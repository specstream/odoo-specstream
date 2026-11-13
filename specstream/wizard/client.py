import json
import urllib.error
import urllib.request

from odoo import _
from odoo.exceptions import UserError

API = "https://api.specstream.ai"


def _refusal(error):
    """The API's own words for a refused call, else its status code."""
    try:
        message = json.loads(error.read().decode())["error"]["message"]
    except (ValueError, KeyError, TypeError, AttributeError, OSError):
        message = ""
    if isinstance(message, str) and message.strip():
        return _("SpecStream returned error %s: %s", error.code, message.strip())
    return _("SpecStream returned error %s. Check the API key and the request.", error.code)


def call(path, key, body=None, timeout=90):
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        raise UserError(_refusal(error))
    except (urllib.error.URLError, TimeoutError):
        raise UserError(_("Couldn't reach SpecStream. Check the connection and try again."))
    except ValueError:
        raise UserError(_("Couldn't read the response from SpecStream. Try again in a moment."))
    if not isinstance(payload, dict):
        return {}
    return payload.get("data", payload)


def api_key(env):
    key = env["ir.config_parameter"].sudo().get_param("specstream.api_key")
    if not key:
        raise UserError(_("Add your SpecStream API key in Settings > SpecStream first."))
    return key
