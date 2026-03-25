from pathlib import Path

from tests import conftest


def test_resolve_test_klayout_bin_prefers_environment_variable(monkeypatch):
    monkeypatch.setenv("KLAYOUT_BIN", "/opt/klayout/bin/klayout")
    monkeypatch.setattr(conftest, "_which_klayout", lambda: None)

    assert conftest._resolve_test_klayout_bin() == Path("/opt/klayout/bin/klayout")


def test_resolve_test_klayout_bin_falls_back_to_path_lookup(monkeypatch):
    monkeypatch.delenv("KLAYOUT_BIN", raising=False)
    monkeypatch.setattr(conftest, "_which_klayout", lambda: "/usr/bin/klayout")

    assert conftest._resolve_test_klayout_bin() == Path("/usr/bin/klayout")
