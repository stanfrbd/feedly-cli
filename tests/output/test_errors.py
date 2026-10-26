from feedly_cli import output


def test_error_defaults_to_stderr_and_literal(capsys):
    output.render_error("bad_request", "[red]unsafe[/red]\x1b[2J")
    captured = capsys.readouterr()
    assert not captured.out
    assert "[red]unsafe[/red]" in captured.err
    assert "\x1b" not in captured.err
