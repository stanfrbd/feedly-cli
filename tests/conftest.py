"""Shared safeguards for a deterministic, entirely offline test suite."""

import socket

import pytest


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    """Require mocks for network access and never use a contributor's token."""
    monkeypatch.delenv("FEEDLY_TOKEN", raising=False)

    def deny_network(*args, **kwargs):
        raise AssertionError("Network access is disabled in tests; mock the HTTP response.")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)
