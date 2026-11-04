from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    specstream_api_key = fields.Char(
        string="SpecStream API key",
        config_parameter="specstream_leads.api_key",
        help="Create one under Agents & API at https://specstream.ai/workspace",
    )
