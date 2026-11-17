from feedly_cli import output


def test_error_defaults_to_stderr_and_literal(capsys):
    output.render_error("bad_request", "[red]unsafe[/red]\x1b[2J")
    captured = capsys.readouterr()
    assert not captured.out
    assert "[red]unsafe[/red]" in captured.err
    assert "\x1b" not in captured.err


def test_matching_entry_ids_are_literal_and_control_free(capsys):
    output.render_error(
        "api_error",
        "ambiguous",
        details={"matchingEntryIds": ["[red]entry[/red]\x1b[2J\nnext"]},
    )
    captured = capsys.readouterr()
    assert not captured.out
    assert "  [red]entry[/red] next\n" in captured.err
    assert "\x1b" not in captured.err
