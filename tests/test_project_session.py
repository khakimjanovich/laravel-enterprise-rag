import json

from project_session import (
    get_active_domain,
    get_active_scope,
    load_projects,
    register_project,
    save_projects,
    set_active_domain,
    set_active_project,
    set_active_scope,
)


def test_set_active_domain_persists_ai(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    set_active_domain("ai")

    assert get_active_domain() == "ai"


def test_set_active_scope_persists_package_scope(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    set_active_scope("package:svgate-sdk")

    assert get_active_scope() == "package:svgate-sdk"


def test_load_projects_returns_empty_mapping_by_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert load_projects() == {"projects": {}}


def test_register_project_writes_registry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    register_project("billing", "/tmp/billing.project.contract.json")

    registry = json.loads((tmp_path / "projects.json").read_text(encoding="utf-8"))
    assert registry["projects"]["billing"] == "/tmp/billing.project.contract.json"


def test_set_active_project_writes_contract_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_projects({"projects": {"billing": "/tmp/billing.project.contract.json"}})

    assert set_active_project("billing") is True
    assert (tmp_path / ".active_project").read_text(encoding="utf-8") == "/tmp/billing.project.contract.json"
