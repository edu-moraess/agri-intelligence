#!/usr/bin/env python3
"""Run deterministic Phase 0 checks without following or modifying untrusted paths."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "phase_0_validation_report.json"
MAX_SCANNABLE_BYTES = 5 * 1024 * 1024
PROCESS_TIMEOUT_SECONDS = 30
EXCLUDED_DIRECTORIES = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
PROHIBITED_SUFFIXES = {".pt", ".pth", ".onnx", ".safetensors", ".ckpt", ".bin", ".pkl", ".pickle", ".pem", ".key", ".crt", ".cer", ".der", ".dmp", ".dump"}
PROHIBITED_NAMES = {".env", ".env.local", ".env.production", ".env.development"}
SECRET_PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("jwt_like_token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
)
ASSIGNMENT_PATTERN = re.compile(r'''(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|password|secret)\b\s*[:=]\s*["']([^"']{8,})["']''')
PLACEHOLDERS = {"changeme", "change-me", "replace-me", "your-token-here", "your_api_key", "example", "placeholder", "dummy", "redacted", "fake-token", "not-a-secret"}

@dataclass(frozen=True)
class ScanFile:
    path: Path
    is_binary: bool = False


def _absolute(path: Path) -> Path:
    return Path(path).absolute()


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def load_validation_config(root: Path = ROOT) -> tuple[str, dict[str, Any], str]:
    """Load the deliberately small YAML subset used by validation.yaml."""
    config_path = root / "configs" / "validation.yaml"
    try:
        lines = config_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return "failed", {}, f"configuration unreadable: {type(exc).__name__}"
    required: list[str] = []
    excluded: list[str] = []
    section = ""
    max_bytes = MAX_SCANNABLE_BYTES
    report_path = "artifacts/phase_0_validation_report.json"
    for raw in lines:
        line = raw.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            section = stripped[:-1]
            continue
        if stripped.startswith("-"):
            value = stripped[1:].strip()
            if section == "required_checks":
                required.append(value)
            elif section == "excluded_directories":
                excluded.append(value)
            continue
        key_value = re.match(r"^\s+([A-Za-z0-9_]+):\s*(.*?)\s*$", line)
        if not key_value:
            continue
        key, value = key_value.groups()
        if key == "excluded_directories" and not value:
            section = "excluded_directories"
            continue
        if section == "scanner" and key == "max_scannable_bytes":
            try:
                max_bytes = int(value)
            except ValueError:
                return "failed", {}, "scanner.max_scannable_bytes is not an integer"
        elif section == "scanner" and key == "report_path":
            report_path = value.strip('"\'')
    if not required:
        return "failed", {}, "required_checks is missing or empty"
    if max_bytes <= 0 or not report_path or not excluded:
        return "failed", {}, "scanner configuration is incomplete"
    return "passed", {"required_checks": required, "max_scannable_bytes": max_bytes, "report_path": report_path, "excluded_directories": set(excluded)}, "validation.yaml interpreted"


def iter_repository_files(root: Path, *, report: Path | None = None, authorized_root: Path | None = None, excluded_directories: set[str] | None = None) -> tuple[list[ScanFile], list[str]]:
    """Enumerate files without following symlinks and only inside an authorized root."""
    original_root = _absolute(Path(root))
    if original_root.is_symlink():
        return [], ["invalid_scan_root:root_is_symlink"]
    if not original_root.is_dir():
        return [], ["invalid_scan_root:not_a_directory"]
    resolved_root = original_root.resolve(strict=True)
    if authorized_root is not None:
        authorized = _absolute(Path(authorized_root))
        if authorized.is_symlink() or not path_is_within(resolved_root, authorized):
            return [], ["invalid_scan_root:outside_authorized_root"]
    root = resolved_root
    excluded = EXCLUDED_DIRECTORIES if excluded_directories is None else excluded_directories
    findings: list[str] = []
    files: list[ScanFile] = []
    report_resolved = report.resolve(strict=False) if report else None

    def visit(directory: Path) -> None:
        try:
            entries = list(directory.iterdir())
        except OSError as exc:
            findings.append(f"read_error:{directory.relative_to(root)}:{type(exc).__name__}")
            return
        for entry in sorted(entries, key=lambda p: p.name):
            relative = entry.relative_to(root)
            if entry.is_symlink():
                findings.append(f"symlink:{relative}")
                continue
            if entry.is_dir():
                if entry.name in excluded:
                    continue
                visit(entry)
                continue
            if not entry.is_file():
                continue
            if report_resolved and entry.resolve(strict=False) == report_resolved:
                continue
            try:
                with entry.open("rb") as handle:
                    is_binary = b"\x00" in handle.read(4096)
            except OSError as exc:
                findings.append(f"read_error:{relative}:{type(exc).__name__}")
                continue
            files.append(ScanFile(entry, is_binary))

    visit(root)
    return files, findings


def find_secret_indicators(content: str) -> list[str]:
    found = [name for name, pattern in SECRET_PATTERNS if pattern.search(content)]
    for match in ASSIGNMENT_PATTERN.finditer(content):
        value = match.group(1).strip()
        if value.lower() not in PLACEHOLDERS and not value.startswith(("$", "{", "os.environ")):
            found.append("hardcoded_credential_assignment")
            break
    return sorted(set(found))


def _read_limited_text(path: Path, max_bytes: int) -> tuple[str, str | None]:
    """Read at most max_bytes plus one byte, detecting growth without unbounded memory."""
    chunks: list[bytes] = []
    total = 0
    try:
        with path.open("rb") as handle:
            while total <= max_bytes:
                chunk = handle.read(min(64 * 1024, max_bytes + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > max_bytes:
                    return "", "file_too_large"
            data = b"".join(chunks)
    except OSError as exc:
        return "", f"read_error:{type(exc).__name__}"
    if b"\x00" in data:
        return "", "binary"
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError:
        return "", "read_error:UnicodeDecodeError"


def run_secret_scan(root: Path = ROOT, *, report: Path | None = None, max_bytes: int = MAX_SCANNABLE_BYTES, excluded_directories: set[str] | None = None) -> tuple[str, str]:
    files, traversal_findings = iter_repository_files(root, report=report, excluded_directories=excluded_directories)
    findings = list(traversal_findings)
    checked = 0
    for item in files:
        relative = item.path.relative_to(root)
        content, error = _read_limited_text(item.path, max_bytes)
        if error == "binary":
            continue
        if error:
            findings.append(f"{error}:{relative}")
            continue
        checked += 1
        indicators = find_secret_indicators(content)
        if indicators:
            findings.append(f"{relative}:{','.join(indicators)}")
    return ("failed", "; ".join(findings)) if findings else ("passed", f"checked {checked} text files; binary files handled without decoding")


def run_python_compile(root: Path = ROOT, *, excluded_directories: set[str] | None = None) -> tuple[str, str]:
    files, traversal_findings = iter_repository_files(root, excluded_directories=excluded_directories)
    errors = list(traversal_findings)
    checked = 0
    for item in files:
        if item.path.suffix != ".py":
            continue
        try:
            source, error = _read_limited_text(item.path, MAX_SCANNABLE_BYTES)
            if error:
                errors.append(f"{item.path.relative_to(root)}:{error}")
                continue
            compile(source, str(item.path.relative_to(root)), "exec")
            checked += 1
        except SyntaxError as exc:
            errors.append(f"{item.path.relative_to(root)}:{exc}")
    return ("failed", "; ".join(errors)) if errors else ("passed", f"{checked} Python files compiled in memory")


def run_artifact_scan(root: Path = ROOT, *, report: Path | None = None, max_bytes: int = MAX_SCANNABLE_BYTES, excluded_directories: set[str] | None = None) -> tuple[str, str]:
    files, traversal_findings = iter_repository_files(root, report=report, excluded_directories=excluded_directories)
    findings = list(traversal_findings)
    for item in files:
        name = item.path.name.lower()
        if item.path.suffix.lower() in PROHIBITED_SUFFIXES or name in PROHIBITED_NAMES or name.startswith(".env."):
            findings.append(str(item.path.relative_to(root)))
        try:
            if item.path.stat().st_size > max_bytes:
                findings.append(f"file_too_large:{item.path.relative_to(root)}")
        except OSError as exc:
            findings.append(f"stat_error:{item.path.relative_to(root)}:{type(exc).__name__}")
    return ("failed", ", ".join(findings)) if findings else ("passed", "no prohibited artifacts, unsafe links or oversized files found")


def run_structural_tests(root: Path = ROOT) -> tuple[str, str]:
    try:
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=root, capture_output=True, text=True, check=False, timeout=PROCESS_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return "failed", f"test process exceeded {PROCESS_TIMEOUT_SECONDS}s timeout"
    except OSError as exc:
        return "failed", f"could not start test process: {type(exc).__name__}"
    output = (result.stdout + result.stderr).strip()[-3000:] or "no test output"
    return ("passed", output) if result.returncode == 0 else ("failed", output)


def check_package_import(root: Path = ROOT) -> tuple[str, str]:
    sys.path.insert(0, str(root / "src"))
    try:
        import agri_intelligence
        return "passed", agri_intelligence.__version__
    except Exception as exc:
        return "failed", repr(exc)


def build_report(root: Path = ROOT, report: Path = REPORT) -> dict[str, object]:
    config_status, config, config_detail = load_validation_config(root)
    checks: list[dict[str, object]] = [{"name": "validation_config", "status": config_status, "detail": config_detail}]
    excluded = config.get("excluded_directories", EXCLUDED_DIRECTORIES)
    max_bytes = int(config.get("max_scannable_bytes", MAX_SCANNABLE_BYTES))
    configured_report = root / str(config.get("report_path", report.relative_to(root)))
    actual = {
        "package_import": check_package_import(root),
        "python_compile": run_python_compile(root, excluded_directories=excluded),
        "structural_tests": run_structural_tests(root),
        "secret_scan": run_secret_scan(root, report=configured_report, max_bytes=max_bytes, excluded_directories=excluded),
        "prohibited_artifact_scan": run_artifact_scan(root, report=configured_report, max_bytes=max_bytes, excluded_directories=excluded),
    }
    required = config.get("required_checks", [])
    for name in required:
        if name not in actual:
            checks.append({"name": name, "status": "skipped", "detail": "required check is not implemented or was not executed"})
        else:
            status, detail = actual[name]
            checks.append({"name": name, "status": status, "detail": detail})
    statuses = {str(item["status"]) for item in checks}
    gate = "FAIL" if {"failed", "skipped"} & statuses else ("PASS_WITH_WARNINGS" if "warning" in statuses else "PASS")
    return {"schema_version": "1.3", "phase": 0, "gate": gate, "checks": checks, "limitations": ["No external dataset, model weights or inference were used.", "Scientific performance is not evaluated in Phase 0.", "Pattern-based secret scanning is not a substitute for a dedicated secret scanner or professional security review."]}


def write_report(report: Path, payload: dict[str, object], *, root: Path = ROOT) -> None:
    lexical_root = _absolute(root)
    lexical_artifacts = lexical_root / "artifacts"
    lexical_report = _absolute(report)
    if lexical_report.parent != lexical_artifacts:
        raise ValueError("report destination must be the repository artifacts directory")
    if lexical_root.is_symlink() or not lexical_root.is_dir():
        raise OSError("repository root is not a safe directory")
    if lexical_artifacts.is_symlink() or not lexical_artifacts.is_dir():
        raise OSError("artifacts directory is not a safe directory")
    resolved_root = lexical_root.resolve(strict=True)
    resolved_artifacts = lexical_artifacts.resolve(strict=True)
    if not path_is_within(resolved_artifacts, resolved_root) or resolved_artifacts == resolved_root:
        raise OSError("artifacts directory resolves outside repository root")
    if report.is_symlink():
        raise OSError("refusing to overwrite symlink report destination")
    encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=lexical_artifacts, prefix=".validation-", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(encoded)
    temporary.replace(lexical_report)


def main() -> int:
    config_status, config, _ = load_validation_config(ROOT)
    configured_report = ROOT / str(config.get("report_path", REPORT.relative_to(ROOT))) if config_status == "passed" else REPORT
    payload = build_report(ROOT, configured_report)
    try:
        write_report(configured_report, payload, root=ROOT)
    except (OSError, ValueError) as exc:
        payload["gate"] = "FAIL"
        payload.setdefault("checks", []).append({"name": "report_write", "status": "failed", "detail": type(exc).__name__})
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["gate"] in {"PASS", "PASS_WITH_WARNINGS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
