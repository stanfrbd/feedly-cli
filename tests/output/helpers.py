from io import StringIO

from feedly_cli import output


def human(value, command="search", action=None, **kwargs):
    stream = StringIO()
    output.render(value, command=command, action=action, stream=stream, **kwargs)
    return stream.getvalue()
