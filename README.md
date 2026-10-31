# feedly-cli

A small Python command-line interface for Feedly. Read results in the terminal, export articles as Markdown, or use `--json` for shell scripts and AI agents.

## Install

Requires Python 3.10 or newer. The CLI uses the official `feedly-client` Python package, Rich for terminal output, and markdownify for HTML-to-Markdown conversion.

Install into the current Python environment:

```sh
python -m pip install -e .
```

Or install as an isolated command with uv:

```sh
uv tool install .
```

The command is named `feedly`. You can also run it without installing the script entry point:

```sh
python -m feedly_cli --help
```

## Authentication and permissions

Set `FEEDLY_TOKEN` in the environment. The CLI deliberately has no token command-line option, so credentials do not appear in shell history or process arguments.

```sh
export FEEDLY_TOKEN="your-token"
```

On PowerShell:

```powershell
$env:FEEDLY_TOKEN = "your-token"
```

Use a Feedly token with access to the endpoints you need. Reading a profile, streams, boards, search, or CVE intelligence requires the corresponding Feedly API entitlements. `boards add-url` changes board contents unless `--dry-run` is set, and the token must have permission to edit that board. Feedly may restrict endpoints by plan or token scope.

## Commands

Commands display readable tables or detail views by default. Pass `--json` for the original Feedly response, including continuation tokens. Output flags work before or after subcommands. Redirection does not change the selected format.

```sh
feedly search 'PHP2Shell'
feedly search 'PHP2Shell' --details
feedly search 'PHP2Shell' --all --fetch --json > articles.json
feedly --json boards list
```

```text
feedly profile
feedly folders list
feedly feeds list
feedly articles get ENTRY_ID
feedly articles resolve-url URL [--source-stream STREAM_ID] [--count N] [--max-pages N] [--continuation TOKEN]
feedly streams read STREAM_ID [--count N] [--continuation TOKEN] [--unread-only]
feedly boards list
feedly boards read BOARD_ID [--count N] [--continuation TOKEN]
feedly boards watch BOARD_ID [--interval SECONDS] [--iterations N] [--count N] [--max-pages N]
feedly boards add-url BOARD_ID URL [--source-stream STREAM_ID] [--max-pages N] [--count N] [--dry-run]
feedly boards add-entry BOARD_ID ENTRY_ID
feedly search QUERY [--since DATE] [--before DATE] [--all] [--fetch] [--salience mention|about] [--count N] [--max-pages N] [--continuation TOKEN] [--stream-id STREAM_ID]
feedly search --query-file request.json [--count N] [--continuation TOKEN]
feedly cve CVE_ID
feedly cves get CVE_ID [CVE_ID ...]
feedly cves trending [--count N]
feedly cves search --query-file request.json [--count N] [--continuation TOKEN]
```

Examples:

```sh
feedly profile
feedly streams read 'feed/https://example.com/rss.xml' --count 10
feedly boards read 'user/USER_ID/tag/BOARD_ID' --count 25
feedly search 'semiconductor supply chain'
feedly search 'PHP2Shell' --all --fetch
feedly cves get CVE-2024-12345 CVE-2024-23456
feedly cves trending --count 10
```

Query-file commands accept a JSON object containing the request fields expected by Feedly. Use `-` as the filename to read the JSON object from stdin. Invalid JSON is reported before a Feedly request is made.

```sh
feedly search --query-file search.json
cat vulnerability-query.json | feedly cves search --query-file -
```

### Search all pages and hydrate article details

`search QUERY` returns one Feedly results page. `--all` follows continuation tokens and combines the pages, up to `--max-pages` (default 100). Each page contains at most 100 results by default; use `--count` to choose a smaller page size. Counts and the page limit cannot exceed 100. The command fails with a structured error if the page limit is reached while more results remain, so it never returns a silently truncated result as success. `--continuation` is supported for a single page and cannot be combined with `--all`.

`--fetch` hydrates the results using Feedly's entry lookup API. This adds full metadata Feedly makes available, such as `content`, `fullContent`, or `summary`; it does not fetch article pages from publishers. On a single-page search it hydrates that page. With `--all`, it hydrates the combined result set in batches.

```sh
feedly search 'PHP2Shell' --all --fetch
feedly search 'PHP2Shell' --count 50 --continuation CONTINUATION_TOKEN --fetch
```

### Search a publication date range

Use `--since` (inclusive) and `--before` (exclusive) to select Feedly's **`published`** timestamp, not crawl time. A calendar date means midnight UTC; ISO 8601 timestamps must include a timezone (`Z` or an offset) and may have millisecond precision. For all of October 2026:

```sh
feedly search php2shell --since 2026-10-01 --before 2026-11-01 --all --json
feedly search php2shell --since 2026-10-01 --before 2026-11-01 --all --markdown --brief
feedly search php2shell --since 2026-10-15T09:00:00+02:00 --before 2026-10-16T09:00:00+02:00 --all
```

Either bound can be omitted. Invalid dates, timezone-less timestamps, equal bounds and reversed ranges fail before authentication or network requests. Missing or invalid article `published` timestamps cause an explicit API error for dated searches rather than silently losing undatable articles. Unfiltered searches retain existing behavior. Date flags also work with `--query-file`; the query body remains unchanged.

Bounds are applied locally to each returned Feedly page, without assuming undocumented server-side date semantics or ordering. They preserve Feedly's ordering and continuation tokens. **A single-page search is still only one API page:** `--count` controls the number requested before filtering, so fewer (or zero) matches can be returned while more pages remain. Repeat the same bounds with `--continuation`, or use `--all` for all matching results within the accessible query scope. `--all` drains pages even after an empty filtered page and fails if `--max-pages` is reached with more results remaining. This may scan out-of-range articles and consume more API requests; it does not guarantee access beyond Feedly's account/search history limits. Hydration runs after filtering, so `--fetch` retrieves only matched entries. Date selection is identical in terminal, JSON, brief JSON and Markdown modes.

### Export article content as Markdown

`--markdown` is supported by `articles get`, `search`, `streams read`, `boards read`, and `boards watch`. Without `--json`, it writes plain Markdown documents with article metadata and content, suitable for a file or an agent context.

```sh
feedly articles get ENTRY_ID --markdown > article.md
feedly search 'PHP2Shell' --all --fetch --markdown > articles.md
feedly search 'PHP2Shell' --all --fetch --json --markdown > articles.json
```

Combined with `--json`, it retains the response structure and adds `contentMarkdown` and `contentFormat` to each article. `contentFormat` indicates `content`, `summary`, or `unavailable`. HTML headings, links, lists and code blocks are converted to Markdown. The command uses content already supplied by Feedly and does not download publisher pages; a summary stays a summary. Markdown conversion does not imply `--fetch`, so use both flags when you want full entry lookup.

### Resolve a publisher URL to a Feedly entry

`articles resolve-url` scans an indexed stream without requiring a board or changing account data. It returns `entryId`, `url`, `streamId` and `pagesScanned` with `--json`; terminal output shows complete, copyable values. The default source is the account's enterprise global stream. Use `--source-stream` (alias `--stream-id`) for a specific feed, folder or board; accounts without an enterprise default must supply a source.

```sh
feedly articles resolve-url 'https://www.sophos.com/en-us/blog/chaos-in-teams-vishing' --json
feedly articles resolve-url 'https://www.sophos.com/en-us/blog/chaos-in-teams-vishing' --source-stream 'feed/https://blogs.sophos.com/feed/' --json
feedly articles resolve-url 'https://example.com/article' --source-stream 'feed/https://example.com/rss.xml' --max-pages 20 --count 100 --json
feedly articles get 'ENTRY_ID' --markdown
```

Matching is exact against Feedly's `canonicalUrl`, `url` or `alternate.href`. The command does not follow redirects, remove tracking parameters, normalize trailing slashes, fetch publisher pages, ingest a URL or fabricate an entry ID. Defaults are 100 entries per page and at most 10 pages; each option is bounded to 1–100.

An exhausted source with no exact match returns `not_found` (exit 4), not a claim of global absence from Feedly. Reaching `--max-pages` while a continuation remains returns an **incomplete scan error** (`api_error`, exit 6), not “not found.” Use `--json` to obtain `error.details.continuation`, then repeat with the **same URL and source stream** plus `--continuation TOKEN`. If needed specify the default source's `error.details.streamId` explicitly. Page counts are per invocation, including resumed scans. Invalid API pages or repeated continuations fail explicitly. The command is a resolution record, not article content: `--markdown` and `--brief` are not supported; use `articles get` with the returned entry ID for those formats.

### Construct filtered searches for AI agents

Text queries become one Feedly `customKeyword` part; multiword text such as `feedly search 'Microsoft Teams'` is sent as one keyword/phrase value, not parsed as SQL or a local Boolean expression. For explicit combinations use `--query-file`: **different layers are AND; parts within a layer are OR**, as documented in [Feedly's search guide](https://developers.feedly.com/docs/using-the-search-api). Do not assume literal `AND`, `OR`, dates or `site:` text in a positional query is interpreted as CLI filter syntax.

This complete request searches **(vishing OR phishing) AND Microsoft Teams**:

```json
{
  "layers": [
    {
      "type": "matches",
      "salience": "mention",
      "parts": [
        {"type": "customKeyword", "text": "vishing"},
        {"type": "customKeyword", "text": "phishing"}
      ]
    },
    {
      "type": "matches",
      "salience": "mention",
      "parts": [
        {"type": "customKeyword", "text": "Microsoft Teams"}
      ]
    }
  ]
}
```

Save it as `query.json`, then combine server-side keyword matching with **local publication-date bounds**, exhaustive bounded pagination and metadata hydration:

```sh
feedly search --query-file query.json --since 2026-10-01 --before 2026-11-01 --all --fetch --json --brief
cat query.json | feedly search --query-file - --all --json
```

PowerShell stdin equivalent:

```powershell
Get-Content -Raw query.json | feedly search --query-file - --all --json
```

To constrain a text query's source use `--stream-id STREAM_ID`. With a JSON query, include the source in the body instead (`--stream-id` is rejected with `--query-file`):

```json
{
  "layers": [
    {
      "type": "matches",
      "salience": "about",
      "parts": [{"type": "customKeyword", "text": "vishing"}]
    }
  ],
  "source": {
    "items": [{"type": "stream", "id": "feed/https://example.com/rss.xml"}]
  }
}
```

Replace the example feed ID with an indexed source you can access, or use a returned board/folder stream ID. Text queries default to the discovered enterprise global source; **query-file bodies are sent unchanged**, so an omitted `source` uses Feedly's API/account scope rather than the CLI-injected text-query default.

`--salience about` applies to text queries only; use `"salience": "about"` inside each JSON layer for title/about-focused matches rather than passing `--salience about` alongside `--query-file`. `mention` searches article content and permits passing mentions. Feedly's guide describes `about` as title-focused; semantic matching and result availability are still Feedly-controlled.

For advanced entity/model filters, obtain documented entity IDs or a query exported from Feedly's relevant API-enabled UI; do not substitute labels or invent `filters` structures. The [search guide](https://developers.feedly.com/docs/using-the-search-api) verifies keyword layers and sources; [Ask AI](https://developers.feedly.com/reference/search-ask-ai) and [Vulnerability Agent](https://developers.feedly.com/reference/vulnerability-agent) use different request contracts and may require additional entitlements. Their attachments/dashboard filters are not interchangeable with content search layers.

For agents requiring completeness, keep `--all` and handle nonzero exits instead of interpreting the first `--count` page as the whole range. `--fetch` retrieves Feedly entry metadata only; `--json --brief` is compact triage with explicit `iocStatus`, while raw `--json` retains all returned evidence. Use the same query file/date bounds/source when resuming a continuation.

### Watching a board

`boards watch` polls immediately, drains board pagination up to `--max-pages`, then waits for the configured interval. It displays newly seen articles on each poll. With `--json`, it emits one JSON object per poll (JSON Lines), with already-seen item IDs omitted on later polls. If more pages remain after the page bound, the command reports an error rather than silently skipping entries. The default interval is 60 seconds. By default it runs until interrupted; `--iterations N` bounds the number of polls. Ctrl+C stops the watch cleanly.

```sh
feedly boards watch 'user/USER_ID/tag/BOARD_ID' --interval 30 --iterations 5
```

### Adding a URL to a board

Adding a URL uses the same exact-match bounded resolver as `articles resolve-url`, then adds that article to the selected board. It does not ingest arbitrary URLs from the web. The default source is the global stream derived from the board ID, falling back to the account enterprise global stream; `--source-stream` (alias `--stream-id`) selects another stream. `--max-pages` bounds the scan, and `--dry-run` resolves the article without changing the board. An incomplete scan is an error, not “not found”; `boards add-url` preserves its existing dry-run JSON shape. `boards add-entry` adds an already-known Feedly entry ID directly.

```sh
feedly boards add-url 'user/USER_ID/tag/BOARD_ID' 'https://example.com/article' --dry-run
feedly boards add-url 'user/USER_ID/tag/BOARD_ID' 'https://example.com/article'
feedly boards add-entry 'user/USER_ID/tag/BOARD_ID' 'ENTRY_ID'
```

## Output and exit codes

Article lists show one block per article with its source, publication date, **Feedly entry ID**, **original publisher URL**, **IoC status** and any CVEs Feedly linked to it (with CVSS, exploit and patch flags). IDs and URLs remain complete and copyable even in narrow terminals; an ID can be used directly with `articles get` or `boards add-entry`. The URL comes from Feedly's canonical URL or alternate article link, not a generated Feedly reader link. Missing IDs or URLs are explicitly marked unavailable. Use `--details` to add board labels, malware, threat actors, ATT&CK techniques and Feedly's AI summary. `articles get` always displays those details plus the article content. `cve` and `cves get` show a readable CVE summary (CVSS, EPSS, exploitation, weaknesses, affected products, patch status); use `--json` for every field. Rendering does not make additional API requests. Board membership is shown only when included in Feedly's response. JSON output is unaffected by `--details`.

Terminal listings and Markdown (including `--brief`) show `Indicators: Contains IoC (Feedly: N extracted mentions)` when Feedly supplies a nonempty `indicatorsOfCompromise.mentions` list. This is Feedly's extraction metadata, not a local heuristic or an independently verified maliciousness verdict; the count is mentions, not necessarily unique indicators. An empty list shows `No IoCs reported by Feedly (not proof of absence)`. Missing or unusable metadata shows `Unknown (Feedly IoC metadata unavailable)`. Ordinary article URLs, content links and detection-rule export URLs are never treated as IoCs. Metadata availability depends on Feedly's response and account entitlements; `search --fetch` can retrieve additional entry metadata but cannot guarantee IoC coverage. Raw JSON remains unchanged. Brief JSON adds the stable `iocStatus` field described below while preserving its existing fields.

| Mode | Flags | Use it for |
|---|---|---|
| Human-readable | _(default)_, `--details` | Reading in a terminal |
| JSON | `--json` | Scripts; the full Feedly response (large: about 10 KB per article) |
| Brief JSON | `--json --brief` | Agents; per article only `id`, `title`, `url`, `source`, `published`, `cves`, `malware`, `threatActors`, `techniques`, `summary`, `iocCount`, `iocStatus`; the response envelope (`continuation`, `pages`) is kept |
| Markdown | `--markdown` | Article text and threat facts in an agent context or file |
| Brief Markdown | `--markdown --brief` | Metadata and threat facts only, without article bodies |

`--brief` applies to article, search, stream and board results.

Every brief JSON article has **`iocStatus`**, using the same interpretation as terminal and Markdown:

| Value | Meaning |
|---|---|
| `present` | Feedly provided a nonempty `indicatorsOfCompromise.mentions` list of nonempty objects |
| `not_reported` | Feedly explicitly provided an empty mentions list; not proof the article contains no IoCs |
| `unknown` | Metadata is absent, null or malformed (including non-list mentions or empty/non-object mention records); never treat this as absence |

The existing `iocCount` behavior is preserved for compatibility: positive list lengths are included, zero counts are omitted. Malformed lists can retain a legacy positive count while `iocStatus` is `unknown`; **use the state field for decisions**, not the presence/absence of a count. Counts are extracted mentions, not unique or independently verified malicious indicators. Example records:

```json
[
  {"id":"entry-positive","iocCount":2,"iocStatus":"present"},
  {"id":"entry-empty","iocStatus":"not_reported"},
  {"id":"entry-unavailable","iocStatus":"unknown"}
]
```

Use `feedly search php2shell --all --fetch --json --brief` for compact triage with the available entry metadata. The new field is additive in brief JSON only; raw JSON and JSON+Markdown still preserve Feedly's original metadata without adding `iocStatus`.

For focused October 2026 triage, combine publication bounds, full pagination, entry metadata and about-only matching:

```sh
feedly search php2shell --since 2026-10-01 --before 2026-11-01 --salience about --all --fetch --json --brief
```

### Identifying a specific threat (agent workflow)

Search is broad: by default Feedly returns every article that merely *mentions* the term. An agent identifying one threat (for example `PHP2Shell`) can narrow it down in three read-only steps:

```sh
# 1. Find the articles that are about the threat; each result has an ID, CVEs and a summary.
feedly search 'PHP2Shell' --salience about --count 10 --json --brief

# 2. Read the most relevant article in full, using its "id" from step 1.
feedly articles get 'ENTRY_ID' --markdown

# 3. Look up each CVE listed in step 1 for CVSS, EPSS, exploit and patch status.
feedly cves get CVE-2026-109618 CVE-2026-109619 --json
```

`--salience about` keeps articles centred on the query and drops passing mentions (`--salience mention`, the default, keeps both). It applies to text queries; put `salience` in the JSON body when using `--query-file`. If `continuation` is present in the response, pass it to `--continuation` for the next page. Entry IDs contain `/`, `=` and `:` characters, so quote them in the shell.

Use `--json` explicitly in scripts and agent instructions. JSON output preserves API data without terminal formatting. Errors are written to stderr as readable messages by default, or with this structure when `--json` is set:

```json
{"error":{"code":"not_found","category":"not_found","message":"..."}}
```

| Exit code | Meaning |
|---:|---|
| 0 | Success, including a cleanly interrupted board watch |
| 2 | Invalid command, argument, query file, or local input |
| 3 | Missing token, authentication failure, or permission failure |
| 4 | Requested Feedly resource was not found |
| 5 | Feedly rate limit reached |
| 6 | Network or other Feedly API failure |
| 7 | Unexpected local error |

Feedly API error codes are preserved in the JSON error's `code` field where available. Treat nonzero exit status as failure; do not parse stderr as a successful response.

## API limits

This CLI exposes a focused subset of Feedly operations. Results, pagination behavior, availability, and account limits are determined by Feedly. `--continuation` passes through Feedly's continuation token; use the token from a prior response to request another page. CVE trending requests are limited to 25 items. Board watch polls the current board stream and is subject to normal API rate limits. It does not maintain a durable checkpoint between runs. Enterprise folder and feed listing commands require access to their respective Feedly endpoints.

The CLI does not store credentials, retry API calls, or mark articles as read. Avoid passing sensitive search terms through shell history when that matters; use `--query-file` and stdin instead.

## Safe smoke check

After setting a token, start with read-only commands:

```sh
feedly profile
feedly boards list
feedly search 'CVE-2024-12345'
```

To check URL resolution without a board write, use `boards add-url ... --dry-run`. A normal `boards add-url` call mutates the selected board.

Run `python scripts/smoke.py` for the read-only smoke suite. It never adds articles to boards and reports unavailable entitlements separately. The Vulnerability Agent endpoint can return HTTP 403 even when other CVE commands are available to the same token.

## Development

```sh
python -m pip install -e '.[dev]'
pre-commit install
pre-commit run --all-files
python -m pytest
ruff check .
ruff format --check .
python -m build
```

Pre-commit runs whitespace, YAML and TOML checks, Ruff lint fixes, and Ruff formatting.
Ruff rules and formatting are configured in `.ruff.toml`; CI runs the same hooks.

The transport reuses Feedly's [official Python client](https://github.com/feedly/python-api-client). Endpoint mappings and official documentation links are in [docs/api.md](docs/api.md).

See [CONTRIBUTING.md](CONTRIBUTING.md) for the code layout, extension points and offline mock testing workflow.
