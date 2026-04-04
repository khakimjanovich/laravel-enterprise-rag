import os
import json
import requests
from pathlib import Path
from rich.console import Console

console = Console()

PHP_PROJECT = os.environ.get("PHP_PROJECT", "")
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "deepseek-coder-v2:16b"
OUTPUT_DIR = Path("knowledge/analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCAN_TARGETS = [
    "composer.json",
    "src/**/*.php",
    "packages/**/composer.json",
    "packages/**/src/**/*.php",
]

IGNORE_DIRS = {
    "vendor", "node_modules", ".git",
    "storage", "bootstrap/cache", ".venv"
}

def collect_files(base: Path) -> list[Path]:
    files = []
    for root, dirs, filenames in os.walk(base):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for filename in filenames:
            if filename.endswith((".php", ".json", ".md")):
                files.append(Path(root) / filename)
    return files

def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""

def ask_deepseek(prompt: str) -> str:
    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    })
    return response.json()["response"]

def analyse_package(package_path: Path) -> str:
    composer = read_file(package_path / "composer.json")
    src_files = list((package_path / "src").rglob("*.php")) \
        if (package_path / "src").exists() else []

    src_content = ""
    for f in src_files[:20]:  # cap at 20 files per package
        src_content += f"\n\n### {f.relative_to(package_path)}\n"
        src_content += read_file(f)[:2000]  # cap per file

    prompt = f"""
You are analysing a PHP package inside a Laravel enterprise monorepo.

composer.json:
{composer}

Source files:
{src_content}

Return a markdown report with these exact sections:

## Package Name
## Type
sdk | module | laravel-app | other

## Public Entrypoint
What is the single public class? Is it correctly placed?

## Boundary Violations
List any illuminate/* dependencies found in an SDK package.
List any Laravel facades, helpers (config(), app(), Log::) found in SDK src/.
List any ServiceProvider or Facade classes found in SDK src/.

## Structure Compliance
Does the folder structure match:
src/Contracts/, src/Configs/, src/Data/, src/Exceptions/, src/Internal/?
What is missing or misplaced?

## Observed Conventions
What patterns are consistently used in this package?
Mark each as: confirmed | observed | proposed | violation

## Gaps
What is implemented but not documented?
What conventions are missing from the code entirely?

## Recommended Actions
List concrete fixes in priority order.

Rules:
- Only report what you actually see in the files.
- Never invent structure that is not present.
- Mark absent sections explicitly as: absent
"""
    return ask_deepseek(prompt)

def run():
    if not PHP_PROJECT:
        console.print("[red]PHP_PROJECT env var not set[/red]")
        return

    base = Path(PHP_PROJECT)
    console.print(f"[green]Scanning: {base}[/green]")

    # Find all packages
    packages_dir = base / "packages"
    if packages_dir.exists():
        packages = [p for p in packages_dir.iterdir() if p.is_dir()]
    else:
        packages = [base]

    console.print(f"[green]Found {len(packages)} packages[/green]")

    for package in packages:
        console.print(f"\n[bold]Analysing: {package.name}[/bold]")
        report = analyse_package(package)

        output_file = OUTPUT_DIR / f"{package.name}.md"
        output_file.write_text(f"# Analysis: {package.name}\n\n{report}")
        console.print(f"[green]Saved: {output_file}[/green]")

    console.print("\n[bold green]Analysis complete.[/bold green]")
    console.print(f"Reports saved to: {OUTPUT_DIR}")
    console.print("\nNext: review reports, then run ingestion to load findings into ChromaDB")

if __name__ == "__main__":
    run()
