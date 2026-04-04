import pytest

from project_contract import ProjectContract


def test_app_imports_with_temp_contract(app_module):
    assert app_module.load_project().name == "test-project"


def test_project_contract_reads_env_file(monkeypatch, project_contract_file):
    monkeypatch.setenv("LER_PROJECT_FILE", str(project_contract_file))
    contract = ProjectContract.from_file()
    assert contract.name == "test-project"
    assert contract.knowledge_path() == project_contract_file.parent / "knowledge"


def test_project_contract_missing_file_has_clear_error(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing.contract.json"
    monkeypatch.setenv("LER_PROJECT_FILE", str(missing_path))

    with pytest.raises(FileNotFoundError, match="Project contract file not found"):
        ProjectContract.from_file()


def test_list_local_files_finds_md_files(app_module, project_contract_file):
    knowledge_dir = project_contract_file.parent / "knowledge"
    (knowledge_dir / "sdk").mkdir()
    (knowledge_dir / "sdk" / "guide.md").write_text("# SDK", encoding="utf-8")
    (knowledge_dir / "conventions").mkdir()
    (knowledge_dir / "conventions" / "rules.md").write_text("# Rules", encoding="utf-8")

    files = app_module.list_local_files()
    assert len(files) == 2


def test_list_local_files_only_md(app_module, project_contract_file):
    knowledge_dir = project_contract_file.parent / "knowledge"
    (knowledge_dir / "sdk").mkdir()
    (knowledge_dir / "sdk" / "test.md").write_text("# test", encoding="utf-8")
    (knowledge_dir / "sdk" / "ignore.txt").write_text("ignore", encoding="utf-8")

    files = app_module.list_local_files()
    assert [item["name"] for item in files] == ["sdk/test.md"]


def test_list_local_files_recurses_subfolders(app_module, project_contract_file):
    knowledge_dir = project_contract_file.parent / "knowledge"
    (knowledge_dir / "sdk" / "nested").mkdir(parents=True)
    (knowledge_dir / "sdk" / "nested" / "structure.md").write_text("# structure", encoding="utf-8")

    files = app_module.list_local_files()
    assert files[0]["name"] == "sdk/nested/structure.md"


def test_list_local_files_creates_knowledge_folder(app_module, project_contract_file):
    knowledge_dir = project_contract_file.parent / "knowledge"
    for child in knowledge_dir.iterdir():
        if child.is_file():
            child.unlink()
        else:
            for nested in child.rglob("*"):
                if nested.is_file():
                    nested.unlink()
            for nested in sorted(child.rglob("*"), reverse=True):
                if nested.is_dir():
                    nested.rmdir()
            child.rmdir()
    knowledge_dir.rmdir()

    app_module.list_local_files()
    assert knowledge_dir.exists()


def test_list_local_files_returns_path_name_modified(app_module, project_contract_file):
    knowledge_dir = project_contract_file.parent / "knowledge"
    (knowledge_dir / "sdk").mkdir()
    target = knowledge_dir / "sdk" / "file.md"
    target.write_text("# file", encoding="utf-8")

    files = app_module.list_local_files()
    assert files == [
        {
            "path": str(target),
            "name": "sdk/file.md",
            "modified": target.stat().st_mtime,
        }
    ]


def test_get_embedding_returns_list(app_module):
    result = app_module.get_embedding("How should I structure a PHP SDK?")
    assert isinstance(result, list)


def test_get_embedding_correct_dimensions(app_module):
    result = app_module.get_embedding("test")
    assert len(result) == 4


def test_get_embedding_returns_none_on_error(app_module):
    class BrokenModel:
        def encode(self, text: str):
            raise Exception("fail")

    app_module._model = BrokenModel()
    result = app_module.get_embedding("test")
    assert result is None


def test_get_embedding_different_texts_differ(app_module):
    assert app_module.get_embedding("PHP SDK structure") != app_module.get_embedding("Python data science")


def test_process_file_upserts_chunks(app_module, project_contract_file):
    knowledge_dir = project_contract_file.parent / "knowledge"
    target = knowledge_dir / "sdk.md"
    target.write_text("SDK package structure " * 50, encoding="utf-8")

    app_module.process_file(str(target))
    assert app_module.get_collection().count() >= 1
    assert (project_contract_file.parent / "processed_files.json").exists()


def test_collection_query_returns_results(app_module, project_contract_file):
    knowledge_dir = project_contract_file.parent / "knowledge"
    sdk_doc = knowledge_dir / "sdk.md"
    err_doc = knowledge_dir / "exceptions.md"
    sdk_doc.write_text("SDK package structure package sdk", encoding="utf-8")
    err_doc.write_text("Exception handling error convention", encoding="utf-8")

    app_module.process_file(str(sdk_doc))
    app_module.process_file(str(err_doc))

    embedding = app_module.get_embedding("PHP SDK structure")
    results = app_module.get_collection().query(query_embeddings=[embedding], n_results=2)
    assert len(results["documents"][0]) == 2


def test_collection_query_sdk_structure_relevant(app_module, project_contract_file):
    knowledge_dir = project_contract_file.parent / "knowledge"
    sdk_doc = knowledge_dir / "sdk.md"
    err_doc = knowledge_dir / "exceptions.md"
    sdk_doc.write_text("SDK package structure entrypoint structure", encoding="utf-8")
    err_doc.write_text("Exception handling error convention", encoding="utf-8")

    app_module.process_file(str(sdk_doc))
    app_module.process_file(str(err_doc))

    results = app_module.get_collection().query(
        query_embeddings=[app_module.get_embedding("How should I structure a PHP SDK package?")],
        n_results=1,
    )
    assert "sdk" in results["documents"][0][0].lower()


def test_collection_query_conventions_relevant(app_module, project_contract_file):
    knowledge_dir = project_contract_file.parent / "knowledge"
    sdk_doc = knowledge_dir / "sdk.md"
    convention_doc = knowledge_dir / "conventions.md"
    sdk_doc.write_text("SDK package structure entrypoint", encoding="utf-8")
    convention_doc.write_text("Exception convention confirmed error handling", encoding="utf-8")

    app_module.process_file(str(sdk_doc))
    app_module.process_file(str(convention_doc))

    results = app_module.get_collection().query(
        query_embeddings=[app_module.get_embedding("What conventions apply to exceptions?")],
        n_results=1,
    )
    top = results["documents"][0][0].lower()
    assert "exception" in top or "convention" in top


def test_read_local_file_returns_content(app_module, tmp_path):
    target = tmp_path / "test.md"
    target.write_text("# Hello", encoding="utf-8")
    assert app_module.read_local_file(str(target)) == "# Hello"


def test_read_local_file_returns_empty_on_missing(app_module):
    assert app_module.read_local_file("/nonexistent/path/file.md") == ""
