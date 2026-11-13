# SpecStream

The live web data engine.

One platform to build, search, extract, enrich, map, and monitor data across the entire web.

Ask for any dataset in plain words, and SpecStream builds it from the entire live web: every match found, extracted and enriched into structured records, then monitored for change. It runs through the API and MCP, and inside Sheets, CRMs, Slack, n8n, Zapier and the other tools teams already use.


Three products: the Search API (`GET /v1/web-search`, $5 per 1,000 searches of up to 10 results, or $1 on the fast tier, the most accurate web search API in the world), the Extract API (`POST /v1/extract`, up to 20 URLs a call for web pages, PDF, Word and Excel at $0.80 per 1,000 pages, empty pages free) and Deep Search (structured rows, priced per row). Source URL and read time on every value.
## What the module does

- Creates CRM leads from the rows of a finished SpecStream list.
- Keeps the source URL for every value in the lead description.
- Importing a finished list costs nothing and starts no search.
- Find rows: write what you need in everyday words, read the maximum price, and approve it. Nothing starts before you approve the price. The finished rows become leads, each value with its source URL.
- Search the web and Extract pages call the Search API and the Extract API from CRM > Sales. Set **Speed** to Fast on a search and a fast search costs $1 per 1,000; left empty, no speed is sent and the API's default search runs.
- Watched lists: reads a list again every hour, day or week, and writes each new result, each changed value (before, now and its source URL) and each result no longer in the list to CRM > Sales > Changes. Leads are created and updated from the same rows.
- Scheduled runs: add the id of a schedule you approved in SpecStream, and each check reads the newest list that schedule finished. The module never creates a schedule or sets a spending limit. Run the schedule now starts one run inside the limits you set in SpecStream.

The module is for Odoo 17 and depends on CRM. Its technical name is `specstream`.

## Setup

1. Settings > SpecStream: paste an API key from https://specstream.ai/workspace (Agents & API).
2. CRM > Sales > Import from SpecStream: paste the id of a finished list and set the maximum number of rows.

Each row becomes a lead.

3. CRM > Sales > Find rows (SpecStream): write the request, choose Get the price, then Approve and start. When the list is finished, choose Create leads.

4. CRM > Sales > Watched lists (SpecStream): add a list id, optionally a SpecStream schedule id, and how often to check. A scheduled action checks the due lists every 15 minutes. Check now reads the list at once.

## License

LGPL-3
