"""
services/scan_report_writer.py

Saves a ConventionScanReport to:
  {reports_dir}/{project}/convention-scan-{timestamp}.json
  {reports_dir}/{project}/convention-scan-{timestamp}.md
"""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from services.convention_scanner import ConventionScanReport, ConventionResult


class ScanReportWriter:

    SEVERITY_ICON = {
        "critical": "🔴",
        "major":    "🟠",
        "minor":    "🟡",
        "info":     "🟢",
    }

    STATUS_ICON = {
        "pass":    "✅",
        "fail":    "❌",
        "warning": "⚠️",
        "skip":    "⏭️",
    }

    def __init__(self, reports_dir: str, project_name: str):
        self.dir = Path(reports_dir) / project_name
        self.dir.mkdir(parents=True, exist_ok=True)

    def write(self, report: ConventionScanReport) -> tuple[Path, Path]:
        ts      = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        stem    = f"convention-scan-{ts}"
        json_path = self.dir / f"{stem}.json"
        md_path   = self.dir / f"{stem}.md"

        self._write_json(report, json_path)
        self._write_md(report, md_path)

        return json_path, md_path

    # ── JSON ──────────────────────────────────────────────────────────────────

    def _write_json(self, report: ConventionScanReport, path: Path) -> None:
        data = {
            "project":       report.project,
            "scanned_at":    report.scanned_at,
            "summary": {
                "total_passed":   report.total_passed,
                "total_failed":   report.total_failed,
                "total_warnings": report.total_warnings,
                "critical_count": len(report.all_critical),
            },
            "packages": [
                {
                    "package":  p.package,
                    "layer":    p.layer,
                    "path":     p.path,
                    "passed":   p.passed,
                    "failed":   p.failed,
                    "warnings": p.warnings,
                    "results":  [asdict(r) for r in p.results],
                }
                for p in report.packages
            ],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Markdown ──────────────────────────────────────────────────────────────

    def _write_md(self, report: ConventionScanReport, path: Path) -> None:
        lines = []

        # Header
        lines += [
            f"# Convention Scan Report",
            f"",
            f"**Project:** `{report.project}`  ",
            f"**Scanned:** {report.scanned_at}  ",
            f"",
            f"---",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| ✅ Passed   | {report.total_passed} |",
            f"| ❌ Failed   | {report.total_failed} |",
            f"| ⚠️ Warnings | {report.total_warnings} |",
            f"| 🔴 Critical | {len(report.all_critical)} |",
            f"",
        ]

        # Critical failures first
        if report.all_critical:
            lines += [
                f"---",
                f"",
                f"## 🔴 Critical Failures — Fix These First",
                f"",
            ]
            for r in report.all_critical:
                lines += [
                    f"### `{r.package}` — {r.convention}",
                    f"",
                    f"- **Layer:** `{r.layer}`",
                    f"- **Evidence:** {r.evidence}",
                ]
                if r.file:
                    lines.append(f"- **File:** `{r.file}`" + (f" line {r.line}" if r.line else ""))
                lines.append("")

        # Per-package results
        lines += [
            f"---",
            f"",
            f"## Results By Package",
            f"",
        ]

        for pkg in report.packages:
            icon = "✅" if pkg.failed == 0 else "❌"
            lines += [
                f"### {icon} `{pkg.package}` ({pkg.layer})",
                f"",
                f"Path: `{pkg.path}`  ",
                f"Passed: {pkg.passed} | Failed: {pkg.failed} | Warnings: {pkg.warnings}",
                f"",
            ]

            # Group by status
            failures = [r for r in pkg.results if r.status == "fail"]
            warnings = [r for r in pkg.results if r.status == "warning"]
            passed   = [r for r in pkg.results if r.status == "pass"]

            if failures:
                lines.append("**Failures:**")
                lines.append("")
                for r in failures:
                    sev  = self.SEVERITY_ICON.get(r.severity, "")
                    file = f" `{r.file}`" if r.file else ""
                    lines.append(f"- {sev} **{r.convention}**{file}")
                    lines.append(f"  - {r.evidence}")
                lines.append("")

            if warnings:
                lines.append("**Warnings:**")
                lines.append("")
                for r in warnings:
                    file = f" `{r.file}`" if r.file else ""
                    lines.append(f"- ⚠️ **{r.convention}**{file}")
                    lines.append(f"  - {r.evidence}")
                lines.append("")

            if passed:
                lines.append("<details>")
                lines.append("<summary>Passed checks</summary>")
                lines.append("")
                for r in passed:
                    file = f" `{r.file}`" if r.file else ""
                    lines.append(f"- ✅ {r.convention}{file}")
                lines.append("")
                lines.append("</details>")
                lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")