import json

from ops import main


def write_contract(tmp_path):
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
    (tmp_path / "packages" / "svgate-sdk").mkdir(parents=True)
    return contract_path


def test_ops_ai_project_add_registers_contract(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    contract_path = write_contract(tmp_path)

    exit_code = main(["ai", "project", "add", "--name", "demo", "--contract", str(contract_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "demo" in captured.out


def test_ops_ai_scope_use_package_sets_active_scope(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    contract_path = write_contract(tmp_path)
    main(["ai", "project", "add", "--name", "demo", "--contract", str(contract_path)])
    main(["ai", "project", "use", "demo"])

    exit_code = main(["ai", "scope", "use", "package", "svgate-sdk"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "package:svgate-sdk" in captured.out


def test_ops_project_analyze_gaps_app_is_stubbed(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    contract_path = write_contract(tmp_path)
    main(["ai", "project", "add", "--name", "demo", "--contract", str(contract_path)])
    main(["ai", "project", "use", "demo"])

    exit_code = main(["project", "analyze", "gaps", "--scope", "app"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "not implemented yet" in captured.out.lower()
