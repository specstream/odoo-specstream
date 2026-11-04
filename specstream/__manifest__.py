{
    "name": "SpecStream",
    "summary": "The live web data engine.",
    "description": (
        "One platform to build, search, extract, enrich, map, and monitor data across the entire web. "
        "Ask for any dataset in plain words, and SpecStream builds it from the entire live web: every match found, extracted and enriched into structured records, then monitored for change. "
        "It runs through the API and MCP, and inside Sheets, CRMs, Slack, n8n, Zapier and the other tools teams already use. "
        "This module creates CRM leads from the rows of a finished SpecStream list and keeps the source URL for every value in the lead description. "
        "It only reads finished lists, so it costs nothing and starts no search."
    ),
    "version": "17.0.1.0.0",
    "category": "Sales/CRM",
    "author": "SpecStream SAS",
    "website": "https://specstream.ai?utm_source=odoo",
    "license": "LGPL-3",
    "depends": ["crm"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "wizard/import_wizard_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
}
