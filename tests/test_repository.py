"""Smoke tests — repository foundation."""
import importlib


def test_domain_importable() -> None:
    importlib.import_module("domain")


def test_state_machine_importable() -> None:
    importlib.import_module("state_machine")


def test_services_importable() -> None:
    importlib.import_module("services")


def test_repositories_importable() -> None:
    importlib.import_module("repositories")


def test_app_entry_point_runs(capsys) -> None:
    import app
    app.main()
    captured = capsys.readouterr()
    assert "AI Research Co-Pilot" in captured.out
