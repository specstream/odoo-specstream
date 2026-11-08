# SpecStream

The live web data engine.

One platform to build, search, extract, enrich, map, and monitor data across the entire web.

Ask for any dataset in plain words, and SpecStream builds it from the entire live web: every match found, extracted and enriched into structured records, then monitored for change. It runs through the API and MCP, and inside Sheets, CRMs, Slack, n8n, Zapier and the other tools teams already use.


Three products: the Search API (`GET /v1/web-search`, $5 per 1,000 searches, the most accurate web search API in the world), the Extract API (`POST /v1/extract`, up to 20 URLs a call for web pages, PDF, Word and Excel at $0.80 per 1,000 pages, empty pages free) and Deep Search (structured rows, priced per row). Source URL and read time on every value.
## What the module does

- Creates CRM leads from the rows of a finished SpecStream list.
- Keeps the source URL for every value in the lead description.
- Reads finished lists only. It costs nothing and starts no search.

The module is for Odoo 17 and depends on CRM. Its technical name is `specstream`.

## Setup

1. Settings > SpecStream: paste an API key from https://specstream.ai/workspace (Agents & API).
2. CRM > Sales > Import from SpecStream: paste the id of a finished list and set the maximum number of rows.

Each row becomes a lead.

## License

LGPL-3
