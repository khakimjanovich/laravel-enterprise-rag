import pytest
import os
from unittest.mock import patch


def test_list_local_files_finds_md_files():
    from app import list_local_files
    files = list_local_files()
    assert len(files) >= 2

def test_list_local_files_only_md(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    knowledge = tmp_path / "knowledge" / "sdk"
    knowledge.mkdir(parents=True)
    (knowledge / "test.md").write_text("# test")
    (knowledge / "ignore.txt").write_text("ignore")
    from app import list_local_files
    files = list_local_files()
    assert all(f["name"].endswith(".md") for f in files)
    assert len(files) == 1

def test_list_local_files_recurses_subfolders():
    from app import list_local_files
    files = list_local_files()
    names = [f["name"] for f in files]
    assert any("sdk" in n for n in names)
    assert any("conventions" in n for n in names)

def test_list_local_files_creates_knowledge_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app import list_local_files
    list_local_files()
    assert os.path.exists(tmp_path / "knowledge")

def test_list_local_files_returns_path_name_modified():
    from app import list_local_files
    files = list_local_files()
    for f in files:
        assert "path" in f
        assert "name" in f
        assert "modified" in f

def test_get_embedding_returns_list():
    from app import get_embedding
    result = get_embedding("How should I structure a PHP SDK?")
    assert isinstance(result, list)

def test_get_embedding_correct_dimensions():
    from app import get_embedding
    result = get_embedding("test")
    assert len(result) == 384

def test_get_embedding_returns_none_on_error():
    from app import get_embedding
    with patch("app.model.encode", side_effect=Exception("fail")):
        result = get_embedding("test")
        assert result is None

def test_get_embedding_different_texts_differ():
    from app import get_embedding
    a = get_embedding("PHP SDK structure")
    b = get_embedding("Python data science")
    assert a != b

def test_collection_has_chunks():
    from app import collection
    assert collection.count() >= 39

def test_collection_query_returns_results():
    from app import collection, get_embedding
    embedding = get_embedding("PHP SDK structure")
    results = collection.query(query_embeddings=[embedding], n_results=2)
    assert "documents" in results
    assert len(results["documents"][0]) == 2

def test_collection_query_sdk_structure_relevant():
    from app import collection, get_embedding
    embedding = get_embedding("How should I structure a PHP SDK package?")
    results = collection.query(query_embeddings=[embedding], n_results=1)
    top = results["documents"][0][0]
    assert any(word in top.lower() for word in ["sdk", "package", "entrypoint", "structure"])

def test_collection_query_conventions_relevant():
    from app import collection, get_embedding
    embedding = get_embedding("What conventions apply to exceptions?")
    results = collection.query(query_embeddings=[embedding], n_results=1)
    top = results["documents"][0][0]
    assert any(word in top.lower() for word in ["exception", "correlation", "confirmed"])

def test_read_local_file_returns_content(tmp_path):
    f = tmp_path / "test.md"
    f.write_text("# Hello")
    from app import read_local_file
    content = read_local_file(str(f))
    assert content == "# Hello"

def test_read_local_file_returns_empty_on_missing():
    from app import read_local_file
    result = read_local_file("/nonexistent/path/file.md")
    assert result == ""
