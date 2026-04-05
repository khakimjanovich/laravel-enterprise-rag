"""
services/convention_scanner.py

Scans the real Laravel monorepo against confirmed conventions from
knowledge/conventions/CONVENTIONS.md.

Produces a structured ConventionScanReport saved to:
  {reports_dir}/{project_name}/convention-scan-{timestamp}.json
  {reports_dir}/{project_name}/convention-scan-{timestamp}.md  ← human readable

Usage:
  python scan.py
  python scan.py --package svgate-sdk
  python scan.py --scope sdk
  python scan.py --scope module
"""

import os
import re
import json

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

# ── Types ─────────────────────────────────────────────────────────────────────

Status   = Literal["pass", "fail", "warning", "skip"]
Layer    = Literal["sdk", "module", "app", "unknown"]
Severity = Literal["critical", "major", "minor", "info"]

@dataclass
class ConventionResult:
    convention:  str         # human-readable rule description
    status:      Status      # pass | fail | warning | skip
    severity:    Severity    # critical | major | minor | info
    layer:       Layer       # sdk | module | app | unknown
    package:     str         # e.g. svgate-sdk, module-customers
    evidence:    str         # what the scanner found
    file:        str = ""    # relative file path if applicable
    line:        int = 0     # line number if applicable

@dataclass
class PackageScanResult:
    package:     str
    layer:       Layer
    path:        str
    results:     list[ConventionResult] = field(default_factory=list)

    @property
    def passed(self)  -> int: return sum(1 for r in self.results if r.status == "pass")
    @property
    def failed(self)  -> int: return sum(1 for r in self.results if r.status == "fail")
    @property
    def warnings(self)-> int: return sum(1 for r in self.results if r.status == "warning")
    @property
    def critical_failures(self) -> list[ConventionResult]:
        return [r for r in self.results if r.status == "fail" and r.severity == "critical"]

@dataclass
class ConventionScanReport:
    project:      str
    scanned_at:   str
    packages:     list[PackageScanResult] = field(default_factory=list)

    @property
    def total_passed(self)  -> int: return sum(p.passed   for p in self.packages)
    @property
    def total_failed(self)  -> int: return sum(p.failed   for p in self.packages)
    @property
    def total_warnings(self)-> int: return sum(p.warnings for p in self.packages)
    @property
    def all_critical(self)  -> list[ConventionResult]:
        return [r for p in self.packages for r in p.critical_failures]


# ── Scanner ───────────────────────────────────────────────────────────────────

class ConventionScanner:

    # Illuminate packages that must never appear in SDK composer.json
    ILLUMINATE_PACKAGES = [
        "illuminate/http",
        "illuminate/support",
        "illuminate/container",
        "illuminate/contracts",
        "illuminate/database",
        "illuminate/events",
        "illuminate/foundation",
        "illuminate/log",
        "laravel/framework",
    ]

    # Required directories per layer
    SDK_REQUIRED_DIRS    = ["Contracts", "Configs", "Data", "Exceptions", "Internal"]
    MODULE_REQUIRED_DIRS = ["Adapters", "Actions", "Events", "Listeners",
                            "Commands", "Exceptions", "Filament", "Models", "Providers"]

    # Patterns that must never appear in SDK source files
    SDK_FORBIDDEN_PATTERNS = [
        (r'\bServiceProvider\b',         "ServiceProvider found in SDK",          "critical"),
        (r'\bFacade\b',                  "Facade found in SDK",                   "critical"),
        (r'\bLog::\b',                   "Log facade used in SDK",                "critical"),
        (r'\bconfig\s*\(',               "config() helper used in SDK",           "critical"),
        (r'\bapp\s*\(',                  "app() helper used in SDK",              "critical"),
        (r'Illuminate\\Support\\Facades',"Laravel Facade imported in SDK",        "critical"),
    ]

    # Patterns that must appear in module Adapters/
    TELESCOPE_HTTP_PATTERN = r'Illuminate\\Http\\Client\\Factory'

    def __init__(self, project_root: str, package_roots: list[str]):
        self.root          = Path(project_root)
        self.package_roots = [self.root / pr for pr in package_roots]

    # ── Public entry points ───────────────────────────────────────────────────

    def scan_all(self) -> ConventionScanReport:
        report = ConventionScanReport(
            project    = self.root.name,
            scanned_at = datetime.now(timezone.utc).isoformat(),
        )
        for package_path in self._discover_packages():
            result = self._scan_package(package_path)
            report.packages.append(result)
        return report

    def scan_package(self, name: str) -> ConventionScanReport:
        report = ConventionScanReport(
            project    = self.root.name,
            scanned_at = datetime.now(timezone.utc).isoformat(),
        )
        for package_path in self._discover_packages():
            if package_path.name == name:
                report.packages.append(self._scan_package(package_path))
                return report
        raise ValueError(f"Package '{name}' not found in {self.package_roots}")

    def scan_layer(self, layer: Layer) -> ConventionScanReport:
        report = ConventionScanReport(
            project    = self.root.name,
            scanned_at = datetime.now(timezone.utc).isoformat(),
        )
        for package_path in self._discover_packages():
            detected = self._detect_layer(package_path)
            if detected == layer:
                report.packages.append(self._scan_package(package_path))
        return report

    # ── Package discovery ─────────────────────────────────────────────────────

    def _discover_packages(self) -> list[Path]:
        packages = []
        for root in self.package_roots:
            if not root.exists():
                continue
            for entry in sorted(root.iterdir()):
                if entry.is_dir() and (entry / "composer.json").exists():
                    packages.append(entry)
        return packages

    def _detect_layer(self, path: Path) -> Layer:
        name = path.name.lower()
        if "sdk" in name:
            return "sdk"
        if "module" in name:
            return "module"
        composer = self._read_composer(path)
        if composer:
            require = composer.get("require", {})
            if any("illuminate" in k or "laravel" in k for k in require):
                return "module"
            return "sdk"
        return "unknown"

    # ── Package scanner ───────────────────────────────────────────────────────

    def _scan_package(self, path: Path) -> PackageScanResult:
        layer  = self._detect_layer(path)
        result = PackageScanResult(
            package = path.name,
            layer   = layer,
            path    = str(path.relative_to(self.root)),
        )

        composer = self._read_composer(path)
        src      = path / "src"

        # ── Shared checks ─────────────────────────────────────────────────────
        result.results += self._check_composer_exists(path, layer, composer)
        result.results += self._check_src_exists(path, layer, src)

        if layer == "sdk":
            result.results += self._check_sdk_conventions(path, composer, src)

        elif layer == "module":
            result.results += self._check_module_conventions(path, composer, src)

        return result

    # ── SDK convention checks ─────────────────────────────────────────────────

    def _check_sdk_conventions(
            self, path: Path, composer: dict | None, src: Path
    ) -> list[ConventionResult]:
        results = []
        pkg     = path.name

        # 1. No illuminate/* in composer.json require
        if composer:
            require = composer.get("require", {})
            for illuminate_pkg in self.ILLUMINATE_PACKAGES:
                if illuminate_pkg in require:
                    results.append(ConventionResult(
                        convention = f"SDK has zero illuminate/* dependencies",
                        status     = "fail",
                        severity   = "critical",
                        layer      = "sdk",
                        package    = pkg,
                        evidence   = f"Found forbidden dependency: {illuminate_pkg}",
                        file       = "composer.json",
                    ))

            # confirm psr/log is present
            if "psr/log" not in require:
                results.append(ConventionResult(
                    convention = "PSR-3 logger injected via LoggerInterface (psr/log)",
                    status     = "warning",
                    severity   = "major",
                    layer      = "sdk",
                    package    = pkg,
                    evidence   = "psr/log not found in require — logger may not be injectable",
                    file       = "composer.json",
                ))
            else:
                results.append(ConventionResult(
                    convention = "PSR-3 logger injected via LoggerInterface (psr/log)",
                    status     = "pass",
                    severity   = "info",
                    layer      = "sdk",
                    package    = pkg,
                    evidence   = "psr/log present in require",
                    file       = "composer.json",
                ))

        # 2. Required directories exist in src/
        if src.exists():
            for dirname in self.SDK_REQUIRED_DIRS:
                dir_path = src / dirname
                if dir_path.is_dir():
                    results.append(ConventionResult(
                        convention = f"SDK/{dirname}/ directory exists",
                        status     = "pass",
                        severity   = "info",
                        layer      = "sdk",
                        package    = pkg,
                        evidence   = f"src/{dirname}/ found",
                    ))
                else:
                    sev = "critical" if dirname in ("Contracts", "Exceptions") else "major"
                    results.append(ConventionResult(
                        convention = f"SDK/{dirname}/ directory exists",
                        status     = "fail",
                        severity   = sev,
                        layer      = "sdk",
                        package    = pkg,
                        evidence   = f"src/{dirname}/ missing",
                    ))

        # 3. Single public entrypoint
        results += self._check_single_entrypoint(path, src, "sdk")

        # 4. Scan PHP files for forbidden patterns
        if src.exists():
            for php_file in src.rglob("*.php"):
                # Skip Internal/ — allowed to have more complex internals
                rel = php_file.relative_to(src)
                content = php_file.read_text(encoding="utf-8", errors="ignore")

                for pattern, message, severity in self.SDK_FORBIDDEN_PATTERNS:
                    if re.search(pattern, content):
                        results.append(ConventionResult(
                            convention = f"SDK source must not contain: {message}",
                            status     = "fail",
                            severity   = severity,
                            layer      = "sdk",
                            package    = pkg,
                            evidence   = message,
                            file       = str(rel),
                        ))

        # 5. Contracts/ contains only interfaces
        contracts_dir = src / "Contracts"
        if contracts_dir.is_dir():
            for php_file in contracts_dir.glob("*.php"):
                content = php_file.read_text(encoding="utf-8", errors="ignore")
                if re.search(r'\binterface\b', content):
                    results.append(ConventionResult(
                        convention = "Contracts/ contains only interfaces",
                        status     = "pass",
                        severity   = "info",
                        layer      = "sdk",
                        package    = pkg,
                        evidence   = f"{php_file.name} is an interface",
                        file       = f"src/Contracts/{php_file.name}",
                    ))
                elif re.search(r'\bclass\b', content):
                    results.append(ConventionResult(
                        convention = "Contracts/ contains only interfaces",
                        status     = "fail",
                        severity   = "major",
                        layer      = "sdk",
                        package    = pkg,
                        evidence   = f"{php_file.name} is a class — only interfaces allowed in Contracts/",
                        file       = f"src/Contracts/{php_file.name}",
                    ))

        # 6. Exceptions — check final class and factory methods
        exceptions_dir = src / "Exceptions"
        if exceptions_dir.is_dir():
            for php_file in exceptions_dir.glob("*.php"):
                content = php_file.read_text(encoding="utf-8", errors="ignore")
                is_final   = bool(re.search(r'\bfinal\s+class\b', content))
                has_static = bool(re.search(r'\bpublic\s+static\s+function\b', content))

                results.append(ConventionResult(
                    convention = "SDK exception class is final",
                    status     = "pass" if is_final else "fail",
                    severity   = "info" if is_final else "major",
                    layer      = "sdk",
                    package    = pkg,
                    evidence   = f"{php_file.name} is {'final' if is_final else 'NOT final'}",
                    file       = f"src/Exceptions/{php_file.name}",
                ))
                results.append(ConventionResult(
                    convention = "SDK exception uses static factory methods",
                    status     = "pass" if has_static else "warning",
                    severity   = "info" if has_static else "minor",
                    layer      = "sdk",
                    package    = pkg,
                    evidence   = f"{php_file.name} {'has' if has_static else 'missing'} static factory methods",
                    file       = f"src/Exceptions/{php_file.name}",
                ))

        return results

    # ── Module convention checks ──────────────────────────────────────────────

    def _check_module_conventions(
            self, path: Path, composer: dict | None, src: Path
    ) -> list[ConventionResult]:
        results = []
        pkg     = path.name

        # 1. Required directories
        if src.exists():
            for dirname in self.MODULE_REQUIRED_DIRS:
                dir_path = src / dirname
                sev      = "critical" if dirname in ("Adapters", "Providers") else "major"
                results.append(ConventionResult(
                    convention = f"Module/{dirname}/ directory exists",
                    status     = "pass" if dir_path.is_dir() else "fail",
                    severity   = "info" if dir_path.is_dir() else sev,
                    layer      = "module",
                    package    = pkg,
                    evidence   = f"src/{dirname}/ {'found' if dir_path.is_dir() else 'missing'}",
                ))

        # 2. TelescopeHttpClient uses Illuminate\Http\Client\Factory
        adapters_dir = src / "Adapters"
        if adapters_dir.is_dir():
            telescope_files = list(adapters_dir.glob("*HttpClient*.php"))
            if not telescope_files:
                results.append(ConventionResult(
                    convention = "TelescopeHttpClient implements HttpClientInterface",
                    status     = "fail",
                    severity   = "critical",
                    layer      = "module",
                    package    = pkg,
                    evidence   = "No *HttpClient*.php found in src/Adapters/",
                ))
            else:
                for f in telescope_files:
                    content    = f.read_text(encoding="utf-8", errors="ignore")
                    uses_factory = bool(re.search(self.TELESCOPE_HTTP_PATTERN, content))
                    uses_guzzle  = bool(re.search(r'GuzzleHttp|\\Client\\Client', content))
                    uses_curl    = bool(re.search(r'\bcurl_\w+\b', content))

                    results.append(ConventionResult(
                        convention = "TelescopeHttpClient uses Illuminate\\Http\\Client\\Factory",
                        status     = "pass" if uses_factory else "fail",
                        severity   = "info" if uses_factory else "critical",
                        layer      = "module",
                        package    = pkg,
                        evidence   = (
                            "Illuminate\\Http\\Client\\Factory found"
                            if uses_factory
                            else "Factory NOT found — Telescope will not see outbound calls"
                        ),
                        file       = f"src/Adapters/{f.name}",
                    ))
                    if uses_guzzle:
                        results.append(ConventionResult(
                            convention = "Raw Guzzle or curl in adapters is a boundary violation",
                            status     = "fail",
                            severity   = "critical",
                            layer      = "module",
                            package    = pkg,
                            evidence   = "GuzzleHttp found in adapter — replace with Illuminate HTTP",
                            file       = f"src/Adapters/{f.name}",
                        ))
                    if uses_curl:
                        results.append(ConventionResult(
                            convention = "Raw Guzzle or curl in adapters is a boundary violation",
                            status     = "fail",
                            severity   = "critical",
                            layer      = "module",
                            package    = pkg,
                            evidence   = "curl_* found in adapter — replace with Illuminate HTTP",
                            file       = f"src/Adapters/{f.name}",
                        ))

        # 3. ServiceProvider exists and registers bindings
        providers_dir = src / "Providers"
        if providers_dir.is_dir():
            provider_files = list(providers_dir.glob("*ServiceProvider.php"))
            if not provider_files:
                results.append(ConventionResult(
                    convention = "Module service provider registers all bindings",
                    status     = "fail",
                    severity   = "critical",
                    layer      = "module",
                    package    = pkg,
                    evidence   = "No *ServiceProvider.php found in src/Providers/",
                ))
            else:
                for f in provider_files:
                    content      = f.read_text(encoding="utf-8", errors="ignore")
                    has_register = bool(re.search(r'function\s+register\s*\(', content))
                    has_bind     = bool(re.search(r'\$this->app->(?:bind|singleton)\s*\(', content))
                    has_boot     = bool(re.search(r'function\s+boot\s*\(', content))
                    has_mig      = bool(re.search(r'loadMigrationsFrom', content))

                    results.append(ConventionResult(
                        convention = "Module service provider has register() with bindings",
                        status     = "pass" if (has_register and has_bind) else "fail",
                        severity   = "info" if (has_register and has_bind) else "critical",
                        layer      = "module",
                        package    = pkg,
                        evidence   = (
                            "register() with app->bind/singleton found"
                            if (has_register and has_bind)
                            else "register() or bindings missing"
                        ),
                        file       = f"src/Providers/{f.name}",
                    ))
                    results.append(ConventionResult(
                        convention = "Module owns its migrations — loadMigrationsFrom in provider",
                        status     = "pass" if has_mig else "warning",
                        severity   = "info" if has_mig else "minor",
                        layer      = "module",
                        package    = pkg,
                        evidence   = (
                            "loadMigrationsFrom found"
                            if has_mig
                            else "loadMigrationsFrom missing — migrations may not auto-load"
                        ),
                        file       = f"src/Providers/{f.name}",
                    ))

        # 4. Migrations directory exists
        migrations_dir = path / "database" / "migrations"
        results.append(ConventionResult(
            convention = "Module owns its migrations in database/migrations/",
            status     = "pass" if migrations_dir.is_dir() else "warning",
            severity   = "info" if migrations_dir.is_dir() else "minor",
            layer      = "module",
            package    = pkg,
            evidence   = (
                "database/migrations/ found"
                if migrations_dir.is_dir()
                else "database/migrations/ missing"
            ),
        ))

        # 5. smsxabar — only in customers and pc-manager
        if composer:
            require = composer.get("require", {})
            has_sms = any("smsxabar" in k.lower() for k in require)
            allowed = pkg.lower() in ("module-customers", "module-pc-manager",
                                      "customers", "pc-manager")
            if has_sms and not allowed:
                results.append(ConventionResult(
                    convention = "smsxabar only in module-customers and module-pc-manager",
                    status     = "fail",
                    severity   = "major",
                    layer      = "module",
                    package    = pkg,
                    evidence   = f"khakimjanovich/smsxabar found in {pkg} — not allowed here",
                    file       = "composer.json",
                ))
            elif has_sms and allowed:
                results.append(ConventionResult(
                    convention = "smsxabar only in module-customers and module-pc-manager",
                    status     = "pass",
                    severity   = "info",
                    layer      = "module",
                    package    = pkg,
                    evidence   = "smsxabar correctly scoped to this module",
                    file       = "composer.json",
                ))

        # 6. Log entries — scan Actions/ for layer/correlationId/operation
        actions_dir = src / "Actions"
        if actions_dir.is_dir():
            for php_file in actions_dir.rglob("*.php"):
                content     = php_file.read_text(encoding="utf-8", errors="ignore")
                has_log     = bool(re.search(r'\bLog::', content))
                has_layer   = bool(re.search(r"'layer'", content))
                has_corr    = bool(re.search(r"'correlationId'", content))
                has_op      = bool(re.search(r"'operation'", content))
                rel         = php_file.relative_to(src)

                if has_log:
                    missing = [
                        f for f, found in [
                            ("layer", has_layer),
                            ("correlationId", has_corr),
                            ("operation", has_op),
                        ] if not found
                    ]
                    if missing:
                        results.append(ConventionResult(
                            convention = "Every log entry carries layer, correlationId, operation",
                            status     = "fail",
                            severity   = "major",
                            layer      = "module",
                            package    = pkg,
                            evidence   = f"Log call missing fields: {', '.join(missing)}",
                            file       = str(rel),
                        ))
                    else:
                        results.append(ConventionResult(
                            convention = "Every log entry carries layer, correlationId, operation",
                            status     = "pass",
                            severity   = "info",
                            layer      = "module",
                            package    = pkg,
                            evidence   = "layer, correlationId, operation all present",
                            file       = str(rel),
                        ))

        return results

    # ── Shared checks ─────────────────────────────────────────────────────────

    def _check_composer_exists(
            self, path: Path, layer: Layer, composer: dict | None
    ) -> list[ConventionResult]:
        return [ConventionResult(
            convention = "Each package has its own composer.json",
            status     = "pass" if composer is not None else "fail",
            severity   = "info" if composer is not None else "critical",
            layer      = layer,
            package    = path.name,
            evidence   = "composer.json found" if composer else "composer.json missing",
            file       = "composer.json",
        )]

    def _check_src_exists(
            self, path: Path, layer: Layer, src: Path
    ) -> list[ConventionResult]:
        return [ConventionResult(
            convention = "Package has src/ directory",
            status     = "pass" if src.is_dir() else "fail",
            severity   = "info" if src.is_dir() else "critical",
            layer      = layer,
            package    = path.name,
            evidence   = "src/ found" if src.is_dir() else "src/ missing",
        )]

    def _check_single_entrypoint(
            self, path: Path, src: Path, layer: Layer
    ) -> list[ConventionResult]:
        if not src.is_dir():
            return []
        top_level_classes = [
            f for f in src.glob("*.php")
            if f.is_file()
        ]
        if len(top_level_classes) == 1:
            return [ConventionResult(
                convention = "One public entrypoint class per SDK",
                status     = "pass",
                severity   = "info",
                layer      = layer,
                package    = path.name,
                evidence   = f"Single entrypoint: {top_level_classes[0].name}",
                file       = top_level_classes[0].name,
            )]
        elif len(top_level_classes) == 0:
            return [ConventionResult(
                convention = "One public entrypoint class per SDK",
                status     = "fail",
                severity   = "critical",
                layer      = layer,
                package    = path.name,
                evidence   = "No top-level class found in src/",
            )]
        else:
            return [ConventionResult(
                convention = "One public entrypoint class per SDK",
                status     = "warning",
                severity   = "major",
                layer      = layer,
                package    = path.name,
                evidence   = f"Multiple top-level classes: {[f.name for f in top_level_classes]}",
            )]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _read_composer(self, path: Path) -> dict | None:
        composer_path = path / "composer.json"
        if not composer_path.exists():
            return None
        try:
            return json.loads(composer_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None