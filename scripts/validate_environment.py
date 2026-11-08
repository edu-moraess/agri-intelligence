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

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "phase_0_validation_report.json"
MAX_SCANNABLE_BYTES = 5 * 1024 * 1024
PROCESS_TIMEOUT_SECONDS = 30
EXCLUDED_DIRECTORIES = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
PROHIBITED_SUFFIXES = {
    ".pt", ".pth", ".onnx", ".safetensors", ".ckpt", ".bin", ".pkl", ".pickle",
    ".pem", ".key", ".crt", ".cer", ".der", ".dmp", ".dump",
}
PROHIBITED_NAMES = {".env", ".env.local", ".env.production", ".env.development"}
SECRET_PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("jwt_like_token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
)
ASSIGNMENT_PATTERN = re.compile(
    r'''(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|password|secret)\b\s*[:=]\s*["']([^"']{8,})["']'''
)
PLACEHOLDERS = {
    "changeme", "change-me", "replace-me", "your-token-here", "your_api_key",
    "example", "placeholder", "dummy", "redacted", "fake-token", "not-a-secret",
}

@dataclass(frozen=True)
class ScanFile:
    path: Path
    is_binary: bool = False


def path_is_within(path: Path, root: Path) -> bool:
    """Return true only when the resolved path remains below root."""
    try:
        path.resolve(strict=False).relative_to(root.resolve())
        return True
    except ValueError:
        return False


def iter_repository_files(root: Path, *, report: Path | None = None) -> tuple[list[ScanFile], list[str]]:
    """Enumerate files without following symlinks; return findings for unsafe entries."""
    root = root.resolve()
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
            if entry.is_dir() and not entry.is_symlink():
                if entry.name in EXCLUDED_DIRECTORIES:
                    continue
                visit(entry)
                continue
            if entry.is_symlink():
                findings.append(f"symlink:{relative}")
                continue
            if not entry.is_file():
                continue
            if report_resolved and entry.resolve(strict=False) == report_resolved:
                continue
            if not path_is_within(entry, root):
                findings.append(f"path_outside_root:{relative}")
                continue
            try:
                with entry.open("rb") as handle:
                    is_binary = b"\x00" in handle.read(4096)
            except OSError as exc:
                findings.append(f"read_error:{relative}:{type(exc).__name__}")
                continue
            files.append(ScanFile(entry, is_binary))

    if not root.is_dir() or root.is_symlink():
        return [], ["invalid_scan_root"]
    visit(root)
    return files, findings


def find_secret_indicators(content: str) -> list[str]:
    """Return indicator names only; never return credential-like values."""
    found = [name for name, pattern in SECRET_PATTERNS if pattern.search(content)]
    for match in ASSIGNMENT_PATTERN.finditer(content):
        value = match.group(1).strip()
        if value.lower() not in PLACEHOLDERS and not value.startswith(("$", "{", "os.environ")):
            found.append("hardcoded_credential_assignment")
            break
    return sorted(set(found))


def run_secret_scan(root: Path = ROOT, *, report: Path | None = None) -> tuple[str, str]:
    files, traversal_findings = iter_repository_files(root, report=report)
    findings = list(traversal_findings)
    checked = 0
    for item in files:
        relative = item.path.relative_to(root)
        try:
            size = item.path.stat().st_size
            if size > MAX_SCANNABLE_BYTES:
                findings.append(f"file_too_large:{relative}:{size}")
                continue
            if item.is_binary:
                continue
            content = item.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(f"read_error:{relative}:{type(exc).__name__}")
            continue
        checked += 1
        indicators = find_secret_indicators(content)
        if indicators:
            findings.append(f"{relative}:{','.join(indicators)}")
    if findings:
        return "failed", "; ".join(findings)
    return "passed", f"checked {checked} text files; binary files handled without decoding"


def run_python_compile(root: Path = ROOT) -> tuple[str, str]:
    files, traversal_findings = iter_repository_files(root)
    errors = list(traversal_findings)
    checked = 0
    for item in files:
        if item.path.suffix != ".py":
            continue
        try:
            source = item.path.read_text(encoding="utf-8")
            compile(source, str(item.path.relative_to(root)), "exec")
            checked += 1
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            errors.append(f"{item.path.relative_to(root)}:{exc}")
    return ("failed", "; ".join(errors)) if errors else ("passed", f"{checked} Python files compiled in memory")


def run_artifact_scan(root: Path = ROOT, *, report: Path | None = None) -> tuple[str, str]:
    files, traversal_findings = iter_repository_files(root, report=report)
    findings = list(traversal_findings)
    for item in files:
        name = item.path.name.lower()
        if item.path.suffix.lower() in PROHIBITED_SUFFIXES or name in PROHIBITED_NAMES or name.startswith(".env."):
            findings.append(str(item.path.relative_to(root)))
        try:
            if item.path.stat().st_size > MAX_SCANNABLE_BYTES:
                findings.append(f"file_too_large:{item.path.relative_to(root)}")
        except OSError as exc:
            findings.append(f"stat_error:{item.path.relative_to(root)}:{type(exc).__name__}")
    return ("failed", ", ".join(findings)) if findings else ("passed", "no prohibited artifacts, unsafe links or oversized files found")


def run_structural_tests(root: Path = ROOT) -> tuple[str, str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=root, capture_output=True, text=True, check=False,
            timeout=PROCESS_TIMEOUT_SECONDS,
        )
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
    checks: list[dict[str, object]] = []
    for name, runner in (("package_import", check_package_import), ("python_compile", run_python_compile), ("structural_tests", run_structural_tests)):
        status, detail = runner(root)
        checks.append({"name": name, "status": status, "detail": detail})
    secret_status, secret_detail = run_secret_scan(root, report=report)
    checks.append({"name": "secret_scan", "status": secret_status, "detail": secret_detail})
    artifact_status, artifact_detail = run_artifact_scan(root, report=report)
    checks.append({"name": "prohibited_artifact_scan", "status": artifact_status, "detail": artifact_detail})
    statuses = {str(item["status"]) for item in checks}
    gate = "FAIL" if {"failed", "skipped"} & statuses else ("PASS_WITH_WARNINGS" if "warning" in statuses else "PASS")
    return {
        "schema_version": "1.2", "phase": 0, "gate": gate, "checks": checks,
        "limitations": [
            "No external dataset, model weights or inference were used.",
            "Scientific performance is not evaluated in Phase 0.",
            "Pattern-based secret scanning is not a substitute for a dedicated secret scanner or professional security review.",
        ],
    }


def write_report(report: Path, payload: dict[str, object], *, root: Path = ROOT) -> None:
    """Atomically write only the designated report path."""
    lexical_report = report.absolute()
    lexical_root = root.absolute()
    if lexical_report.parent != lexical_root / "artifacts":
        raise ValueError("report destination must be the repository artifacts directory")
    report.parent.mkdir(exist_ok=True)
    if report.is_symlink():
        raise OSError("refusing to overwrite symlink report destination")
    encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=report.parent, prefix=".validation-", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(encoded)
    temporary.replace(report)


def main() -> int:
    payload = build_report()
    try:
        write_report(REPORT, payload)
    except (OSError, ValueError) as exc:
        payload["gate"] = "FAIL"
        payload.setdefault("checks", []).append({"name": "report_write", "status": "failed", "detail": type(exc).__name__})
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["gate"] in {"PASS", "PASS_WITH_WARNINGS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
