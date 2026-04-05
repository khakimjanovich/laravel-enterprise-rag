import json
from pathlib import Path

def get_saved_project_type(project_root: str) -> str | None:
    contract_file = Path(project_root) / ".ai" / "project.contract.json"

    if not contract_file.exists():
        return None

    try:
        data = json.loads(contract_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    return data.get("project_type")

def detect_project_type(project_root: str) -> str:
    root = Path(project_root)
    composer_file = root / "composer.json"

    if not composer_file.exists():
        return "module"

    try:
        composer = json.loads(composer_file.read_text(encoding="utf-8"))
    except Exception:
        return "module"

    require = composer.get("require", {})
    require_dev = composer.get("require-dev", {})
    deps = set(require) | set(require_dev)

    is_laravel_app = (
            (root / "artisan").exists()
            and (root / "bootstrap" / "app.php").exists()
            and (root / "routes").exists()
            and (root / "app").exists()
            and "laravel/framework" in require
    )
    if is_laravel_app:
        return "laravel-app"

    non_psr_deps = [
        dep for dep in deps
        if not dep.startswith("psr/")
           and dep not in {"php", "ext-json", "ext-curl", "ext-mbstring", "ext-openssl"}
    ]

    is_sdk = (
            (root / "src").exists()
            and not (root / "artisan").exists()
            and not (root / "bootstrap" / "app.php").exists()
            and "laravel/framework" not in require
            and len(non_psr_deps) <= 2
    )
    if is_sdk:
        return "sdk"

    return "module"

def save_detection_result(project_root: str, project_type: str, source: str = "deterministic") -> None:
    root = Path(project_root)
    ai_dir = root / ".ai"
    reports_dir = ai_dir / "reports"
    contract_file = ai_dir / "project.contract.json"
    report_file = reports_dir / "detection.json"

    ai_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "project_type": project_type,
        "source": source,
    }
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    contract = {}
    if contract_file.exists():
        try:
            contract = json.loads(contract_file.read_text(encoding="utf-8"))
        except Exception:
            contract = {}

    contract["project_type"] = project_type
    contract_file.write_text(json.dumps(contract, indent=2), encoding="utf-8")