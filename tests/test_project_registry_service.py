import json

from services.project_registry_service import add_project, current_project, list_projects, use_project


def test_list_projects_returns_registered_names(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "projects.json").write_text(
        json.dumps({"projects": {"billing": "/tmp/billing.contract.json", "crm": "/tmp/crm.contract.json"}}),
        encoding="utf-8",
    )

    projects = list_projects()

    assert [project["name"] for project in projects] == ["billing", "crm"]


def test_add_project_registers_contract(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    add_project("billing", "/tmp/billing.contract.json")

    stored = json.loads((tmp_path / "projects.json").read_text(encoding="utf-8"))
    assert stored["projects"]["billing"] == "/tmp/billing.contract.json"


def test_use_project_sets_active_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "projects.json").write_text(
        json.dumps({"projects": {"billing": "/tmp/billing.contract.json"}}),
        encoding="utf-8",
    )

    assert use_project("billing") is True
    assert (tmp_path / ".active_project").read_text(encoding="utf-8") == "/tmp/billing.contract.json"


def test_current_project_returns_active_mapping(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "projects.json").write_text(
        json.dumps({"projects": {"billing": "/tmp/billing.contract.json"}}),
        encoding="utf-8",
    )
    (tmp_path / ".active_project").write_text("/tmp/billing.contract.json", encoding="utf-8")

    assert current_project() == {"name": "billing", "contract_path": "/tmp/billing.contract.json"}
