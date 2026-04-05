import json

import pytest

from project_contract import ProjectContract


def test_project_contract_reads_service_docs(tmp_path, monkeypatch):
    contract_path = tmp_path / "project.contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "name": "demo",
                "root": str(tmp_path),
                "project_type": "laravel-app",
                "knowledge_dir": str(tmp_path / "knowledge"),
                "reports_dir": str(tmp_path / "reports"),
                "package_roots": [str(tmp_path / "packages")],
                "service_docs": [str(tmp_path / "docs" / "api.pdf")],
                "architecture": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LER_PROJECT_FILE", str(contract_path))

    contract = ProjectContract.from_file()

    assert contract.project_type == "laravel-app"
    assert contract.package_roots == [str(tmp_path / "packages")]
    assert contract.service_docs == [str(tmp_path / "docs" / "api.pdf")]


def test_project_contract_defaults_optional_fields(tmp_path, monkeypatch):
    contract_path = tmp_path / "project.contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "name": "demo",
                "root": str(tmp_path),
                "knowledge_dir": str(tmp_path / "knowledge"),
                "reports_dir": str(tmp_path / "reports"),
                "architecture": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LER_PROJECT_FILE", str(contract_path))

    contract = ProjectContract.from_file()

    assert contract.project_type == "laravel-app"
    assert contract.package_roots == []
    assert contract.service_docs == []


def test_project_contract_raises_for_missing_explicit_file(tmp_path, monkeypatch):
    missing_path = tmp_path / "missing.project.contract.json"
    monkeypatch.setenv("LER_PROJECT_FILE", str(missing_path))

    with pytest.raises(FileNotFoundError, match="Project contract file not found"):
        ProjectContract.from_file()
