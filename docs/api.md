# API coverage

The CLI uses [Feedly's official Python client](https://github.com/feedly/python-api-client), published as `feedly-client`. The adapter configures `https://api.feedly.com`, Bearer authentication from `FEEDLY_TOKEN`, an explicit request timeout, and one attempt per call. Endpoint methods return Feedly JSON without flattening article metadata or continuation tokens.

The [customer script](https://github.com/feedly/sample-customer-scripts/blob/main/python/move-articles/feedly_api.py) was also checked for stream and board request conventions. The official [API reference](https://developers.feedly.com/reference/introduction) is the endpoint contract.

| Workflow | Feedly API | Reference |
| --- | --- | --- |
| Read articles in a board, folder, or AI Feed | `GET /v3/streams/contents` | [Collect articles](https://developers.feedly.com/reference/collect-articles) |
| Read an article | `GET /v3/entries/{entryId}` | [Article metadata](https://developers.feedly.com/reference/get-article-metadata) |
| Fetch matching articles in batches | `POST /v3/entries/.mget` | [Multiple article metadata](https://developers.feedly.com/reference/get-multiple-article-metadata) |
| List Enterprise boards | `GET /v3/enterprise/tags` | [Team boards](https://developers.feedly.com/reference/get-list-of-team-boards) |
| List Enterprise folders | `GET /v3/enterprise/collections` | [Team folders](https://developers.feedly.com/reference/getteamfolders) |
| List AI Feeds | `GET /v3/alerts` | [AI Feeds](https://developers.feedly.com/reference/get-list-of-ai-feeds) |
| Add an indexed article to a board | `PUT /v3/tags/{streamId}` with `entryId` | [Add articles](https://developers.feedly.com/reference/add-articles-to-board) |
| Search articles | `POST /v3/search/contents` | [Search guide](https://developers.feedly.com/docs/using-the-search-api) |
| Read a CVE | `GET /v3/entities/{cveId}` | [CVE metadata](https://developers.feedly.com/reference/cve-insights-card) |
| Read multiple CVEs | `POST /v3/entities/.mget` | [Batch CVE metadata](https://developers.feedly.com/reference/get-multiple-cves) |
| Trending CVEs | `GET /v3/memes/vulnerabilities/en` | [Trending vulnerabilities](https://developers.feedly.com/reference/trending-cves) |
| Query the Vulnerability Agent | `POST /v3/trends/vulnerability-dashboard` | [Vulnerability Agent](https://developers.feedly.com/reference/vulnerability-agent) |

## URL resolution

The current board API accepts article IDs. `boards add-url` finds an exact `canonicalUrl` or `alternate.href` match in a bounded stream scan, then submits its article ID. Use a source stream containing the article for predictable resolution. A miss means the article was not found in the scanned window; it does not prove that Feedly has never indexed it. This command does not ingest an arbitrary external webpage. `--dry-run` resolves the ID without writing to the board.

## Monitoring

`boards watch` is local polling of the stream endpoint. It is not a server-side subscription and does not persist its seen IDs across restarts. Polling and pagination consume the account's normal API quota.

## Search payloads

Plain search text is translated to the documented `matches` layer with a `customKeyword` part. JSON query files are sent as the actual request body; the `RAW_BODY` field shown in some API explorer schemas is an explorer input and is not a wrapper property to send to Feedly. Vulnerability Agent queries should be exported with the **API** button in Feedly and passed as a JSON file.

For an agent request such as "find all Feedly articles about PHP2Shell and fetch them", use:

```sh
feedly search "PHP2Shell" --all --fetch --json > articles.json
```

`--all` follows search continuation tokens. `--fetch` retrieves article metadata in batches through the entries API. Results contain the content available in Feedly, which can include `fullContent`, `content.content`, `summary.content`, and referenced articles under `linked`. A publisher may supply only a summary. This command does not download webpages separately or guarantee the full text of every article. Search scope and history remain subject to Feedly's indexing and account access.

## Validation

Human-readable article output uses Feedly's `canonicalUrl` (with alternate article-link fallbacks) and entry `id` for publisher links and reusable identifiers. IoC descriptions use only the documented `indicatorsOfCompromise.mentions` metadata from [article metadata](https://developers.feedly.com/reference/get-article-metadata). A nonempty list supports a Feedly-attributed contains-IoC description; an empty list reports no extracted mentions, not proof of absence. Missing or malformed metadata is unknown. Export links, Sigma rules and arbitrary content URLs do not establish IoC presence. Rendering does not hydrate entries or fetch publisher pages; use `search --fetch` to request entry metadata explicitly. JSON schemas and brief JSON's existing `iocCount` behavior are unchanged.

Offline tests exercise the CLI and the official SDK with mocked HTTP responses, including write request bodies. `scripts/smoke.py` makes read-only live requests with the caller's token and tests URL resolution with `--dry-run`. Account permissions and API entitlements can limit individual commands even on Enterprise plans.
