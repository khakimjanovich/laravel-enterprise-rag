import json
import os
from typing import Literal

from project_contract import ProjectContract

PROJECT = ProjectContract.from_file()

MEMORY_REVIEW_PATH = str(PROJECT.reports_path() / "memory_review.json")

def _load() -> dict:
    if os.path.exists(MEMORY_REVIEW_PATH):
        with open(MEMORY_REVIEW_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    return {"items": []}


def _save(data: dict) -> None:
    with open(MEMORY_REVIEW_PATH, "w", encoding="utf-8") as f:
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