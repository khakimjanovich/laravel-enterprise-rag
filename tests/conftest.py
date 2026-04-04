import importlib
import json
import sys
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class FakeModel:
    def encode(self, text: str) -> list[float]:
        lowered = text.lower()
        return [
            float(lowered.count("sdk") + lowered.count("package") + lowered.count("structure")),
            float(lowered.count("exception") + lowered.count("error")),
            float(lowered.count("convention") + lowered.count("confirmed")),
            float(len(lowered.split())),
        ]


@pytest.fixture
def project_contract_file(tmp_path: Path) -> Path:
    knowledge_dir = tmp_path / "knowledge"
    reports_dir = tmp_path / "reports"
    chroma_dir = tmp_path / "chroma_db"
    knowledge_dir.mkdir()
    reports_dir.mkdir()
    chroma_dir.mkdir()

    contract_path = tmp_path / "project.contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "name": "test-project",
                "root": str(tmp_path),
                "knowledge_dir": str(knowledge_dir),
                "reports_dir": str(reports_dir),
                "architecture": {},
            }
        ),
        encoding="utf-8",
    )
    return contract_path


@pytest.fixture
def app_module(monkeypatch: pytest.MonkeyPatch, project_contract_file: Path):
    monkeypatch.setenv("LER_PROJECT_FILE", str(project_contract_file))

    for module_name in ("app", "memory_review", "project_contract"):
        sys.modules.pop(module_name, None)

    app = importlib.import_module("app")
    importlib.reload(app)

    monkeypatch.setattr(app, "PERSISTENT_DIRECTORY", str(project_contract_file.parent / "chroma_db"))
    monkeypatch.setattr(app, "COLLECTION_NAME", f"test-{uuid.uuid4()}")
    app._project = None
    app._client = None
    app._collection = None
    app._model = FakeModel()
    return app
