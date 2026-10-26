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
feedly search 'PHP2Shell' --all --fetch --json > articles.json
feedly --json boards list
```

```text
feedly profile
feedly folders list
feedly feeds list
feedly articles get ENTRY_ID
feedly streams read STREAM_ID [--count N] [--continuation TOKEN] [--unread-only]
feedly boards list
feedly boards read BOARD_ID [--count N] [--continuation TOKEN]
feedly boards watch BOARD_ID [--interval SECONDS] [--iterations N] [--count N] [--max-pages N]
feedly boards add-url BOARD_ID URL [--source-stream STREAM_ID] [--max-pages N] [--count N] [--dry-run]
feedly boards add-entry BOARD_ID ENTRY_ID
feedly search QUERY [--all] [--fetch] [--count N] [--max-pages N] [--continuation TOKEN] [--stream-id STREAM_ID]
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

### Export article content as Markdown

`--markdown` is supported by `articles get`, `search`, `streams read`, `boards read`, and `boards watch`. Without `--json`, it writes plain Markdown documents with article metadata and content, suitable for a file or an agent context.

```sh
feedly articles get ENTRY_ID --markdown > article.md
feedly search 'PHP2Shell' --all --fetch --markdown > articles.md
feedly search 'PHP2Shell' --all --fetch --json --markdown > articles.json
```

Combined with `--json`, it retains the response structure and adds `contentMarkdown` and `contentFormat` to each article. `contentFormat` indicates `content`, `summary`, or `unavailable`. HTML headings, links, lists and code blocks are converted to Markdown. The command uses content already supplied by Feedly and does not download publisher pages; a summary stays a summary. Markdown conversion does not imply `--fetch`, so use both flags when you want full entry lookup.

### Watching a board

`boards watch` polls immediately, drains board pagination up to `--max-pages`, then waits for the configured interval. It displays newly seen articles on each poll. With `--json`, it emits one JSON object per poll (JSON Lines), with already-seen item IDs omitted on later polls. If more pages remain after the page bound, the command reports an error rather than silently skipping entries. The default interval is 60 seconds. By default it runs until interrupted; `--iterations N` bounds the number of polls. Ctrl+C stops the watch cleanly.

```sh
feedly boards watch 'user/USER_ID/tag/BOARD_ID' --interval 30 --iterations 5
```

### Adding a URL to a board

Adding a URL scans an indexed Feedly source stream for an exact URL match, then adds that article to the selected board. It does not ingest arbitrary URLs from the web. The default source is Feedly's enterprise global stream; `--source-stream` (alias `--stream-id`) selects another stream. `--max-pages` bounds the scan, and `--dry-run` resolves the article without changing the board. `boards add-entry` adds an already-known Feedly entry ID directly.

```sh
feedly boards add-url 'user/USER_ID/tag/BOARD_ID' 'https://example.com/article' --dry-run
feedly boards add-url 'user/USER_ID/tag/BOARD_ID' 'https://example.com/article'
feedly boards add-entry 'user/USER_ID/tag/BOARD_ID' 'ENTRY_ID'
```

## Output and exit codes

Human output includes available titles, dates, sources, IDs, URLs and board labels. Rendering does not make additional API requests. Board membership is shown only when included in Feedly's response. Narrow terminals use detail views to keep IDs and URLs accessible.

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
