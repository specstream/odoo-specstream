{
    "name": "SpecStream",
    "summary": "The live web data engine.",
    "description": (
        "One platform to build, search, extract, enrich, map, and monitor data across the entire web. "
        "Ask for any dataset in plain words, and SpecStream builds it from the entire live web: every match found, extracted and enriched into structured records, then monitored for change. "
        "It runs through the API and MCP, and inside Sheets, CRMs, Slack, n8n, Zapier and the other tools teams already use. "
        "Three products: the Search API ($5 per 1,000 searches of up to 10 results, or $1 on the fast tier, the most accurate web search API in the world), the Extract API ($0.80 per 1,000 pages for web pages, PDF, Word and Excel) and Deep Search (structured rows priced per row). "
        "This module creates CRM leads from the rows of a finished SpecStream list and keeps the source URL for every value in the lead description. "
        "Under CRM > Sales, Search the web and Extract pages call the Search API and the Extract API from Odoo. Importing a finished list costs nothing and starts no search. "
        "Find rows, also under CRM > Sales, takes a request in everyday words, shows the maximum price, starts only after you approve that price, and turns the finished rows into leads. "
        "Watched lists read a list again every hour, day or week, or the newest list of a schedule you approved in SpecStream, and record each new result, changed value and source URL under CRM > Sales > Changes."
    ),
    "version": "17.0.1.3.0",
    "category": "Sales/CRM",
    "author": "SpecStream SAS",
    "website": "https://specstream.ai?utm_source=odoo",
    "license": "LGPL-3",
    "depends": ["crm"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "wizard/import_wizard_views.xml",
        "wizard/web_wizard_views.xml",
        "wizard/find_wizard_views.xml",
        "views/watch_views.xml",
        "data/ir_cron.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
}
