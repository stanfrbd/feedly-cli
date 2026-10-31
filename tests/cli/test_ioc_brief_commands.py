import json

import pytest


@pytest.mark.parametrize(
    ("argv", "method", "response"),
    [
        (["search", "php2shell"], "search", "envelope"),
        (["articles", "get", "entry"], "entry", "list"),
        (["streams", "read", "stream"], "stream_contents", "envelope"),
        (["boards", "read", "board"], "board_stream", "envelope"),
        (["boards", "watch", "board", "--iterations", "1"], "board_watch", "envelope"),
    ],
)
def test_all_brief_article_commands_include_ioc_state(run_cli, client, argv, method, response):
    items = [
        {"id": "positive", "indicatorsOfCompromise": {"mentions": [{"type": "hash"}]}},
        {"id": "empty", "indicatorsOfCompromise": {"mentions": []}},
        {"id": "missing"},
    ]
    getattr(client, method).return_value = items if response == "list" else {"items": items}
    code, out, err = run_cli([*argv, "--brief"])
    assert code == 0 and not err
    result = json.loads(out)
    records = result if isinstance(result, list) else result["items"]
    assert [item["iocStatus"] for item in records] == ["present", "not_reported", "unknown"]
