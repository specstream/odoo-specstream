{
    "name": "SpecStream Leads",
    "summary": "Pull rows from a SpecStream list into CRM leads, each with its source URL",
    "description": "Paste the id of a finished SpecStream list and create CRM leads from its rows. Every value keeps the page it came from. Reading a finished list costs nothing.",
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
    "installable": True,
    "application": False,
}
