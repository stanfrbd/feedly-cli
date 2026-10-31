import json
import re
from pathlib import Path

import responses


def test_readme_search_json_examples_are_sent_unchanged(
    client, api_http, add_api_response, decode_request_json
):
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")
    section = readme.split("### Construct filtered searches for AI agents", 1)[1].split(
        "### Watching a board", 1
    )[0]
    examples = [
        json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", section, re.DOTALL)
    ]
    assert len(examples) == 2
    parts = examples[0]["layers"]
    assert [part["text"] for part in parts[0]["parts"]] == ["vishing", "phishing"]
    assert parts[1]["parts"] == [{"type": "customKeyword", "text": "Microsoft Teams"}]
    for example in examples:
        add_api_response(api_http, responses.POST, "/v3/search/contents", {"items": []})
        client.search(example)
        assert decode_request_json(api_http.calls[-1]) == example
