import json

import pytest

from project_contract import ProjectContract
from services.scope_service import current_scope, list_scopes, set_scope


@pytest.fixture
def contract(tmp_path):
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
                "service_docs": [],
                "architecture": {},
            }
        ),
        encoding="utf-8",
    )
    packages = tmp_path / "packages"
    (packages / "svgate-sdk").mkdir(parents=True)
    (packages / "billing-sdk").mkdir(parents=True)
    return ProjectContract.from_file(str(contract_path))


def test_scope_service_lists_app_and_package_scopes(contract):
    assert list_scopes(contract) == ["app", "package:billing-sdk", "package:svgate-sdk"]


def test_scope_service_current_scope_defaults_to_app(tmp_path, monkeypatch, contract):
    monkeypatch.chdir(tmp_path)

    assert current_scope(contract) == "app"


def test_scope_service_set_scope_persists_package_scope(tmp_path, monkeypatch, contract):
    monkeypatch.chdir(tmp_path)

    set_scope("package:svgate-sdk", contract)

    assert current_scope(contract) == "package:svgate-sdk"
