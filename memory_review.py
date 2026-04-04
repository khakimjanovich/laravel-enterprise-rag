import json
import os
from typing import Literal

from project_contract import ProjectContract

def _memory_review_path() -> str:
    project = ProjectContract.from_file()
    project.reports_path().mkdir(parents=True, exist_ok=True)
    return str(project.reports_path() / "memory_review.json")

def _load() -> dict:
    memory_review_path = _memory_review_path()
    if os.path.exists(memory_review_path):
        with open(memory_review_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return {"items": []}


def _save(data: dict) -> None:
    with open(_memory_review_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_review_item(
        *,
        kind: Literal["gap", "inconsistency"],
        title: str,
        details: str,
        source: str,
) -> None:
    data = _load()
    data["items"].append(
        {
            "id": len(data["items"]) + 1,
            "kind": kind,
            "title": title,
            "details": details,
            "source": source,
            "status": "open",
        }
    )
    _save(data)


def list_open_items() -> list[dict]:
    return [item for item in _load()["items"] if item["status"] == "open"]


def resolve_item(item_id: int, action: Literal["update_memory", "fix_inconsistency"]) -> bool:
    data = _load()

    for item in data["items"]:
        if item["id"] == item_id and item["status"] == "open":
            item["status"] = action
            _save(data)
            return True

    return False
