#!/usr/bin/env python3
"""Run deterministic Phase 0 checks and emit a machine-readable JSON report."""
from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "phase_0_validation_report.json"
SECRET_PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
)
ASSIGNMENT_PATTERN = re.compile(
    r"""(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|password)\b\s*[:=]\s*["']([^"']{8,})["']"""
)
PLACEHOLDERS = {"changeme", "change-me", "replace-me", "your-token-here", "your_api_key", "example", "placeholder", "dummy", "redacted"}

def find_secret_indicators(content: str) -> list[str]:
    """Return indicator names only; never return credential-like values."""
    found = [name for name, pattern in SECRET_PATTERNS if pattern.search(content)]
    for match in ASSIGNMENT_PATTERN.finditer(content):
        value = match.group(1).strip()
        if value.lower() not in PLACEHOLDERS and not value.startswith(("$", "{", "os.environ")):
            found.append("hardcoded_credential_assignment")
            break
    return sorted(set(found))

def iter_source_files() -> list[Path]:
    excluded = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}
    return sorted(path for path in ROOT.rglob("*") if path.is_file()
                  and not any(part in excluded for part in path.parts) and path != REPORT)

def run_secret_scan() -> tuple[bool, str]:
    findings = []
    for path in iter_source_files():
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        indicators = find_secret_indicators(content)
        if indicators:
            findings.append(f"{path.relative_to(ROOT)}: {','.join(indicators)}")
    return not findings, "; ".join(findings) if findings else "no credential indicators found"

def run_python_compile() -> tuple[bool, str]:
    checked, errors = 0, []
    for path in iter_source_files():
        if path.suffix != ".py":
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path.relative_to(ROOT)), "exec")
            checked += 1
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    return not errors, f"{checked} Python files compiled in memory" if not errors else "; ".join(errors)

def check(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"name": name, "status": "passed" if passed else "failed", "detail": detail}

def main() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    checks = []
    try:
        import agri_intelligence
        checks.append(check("package_import", True, agri_intelligence.__version__))
    except Exception as exc:
        checks.append(check("package_import", False, repr(exc)))

    compiled, detail = run_python_compile()
    checks.append(check("python_compile", compiled, detail))

    try:
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                                cwd=ROOT, capture_output=True, text=True, check=False)
        output = (result.stdout + result.stderr).strip()[-3000:]
        checks.append(check("structural_tests", result.returncode == 0, output or "no test output"))
    except Exception as exc:
        checks.append(check("structural_tests", False, repr(exc)))

    secrets_ok, secrets_detail = run_secret_scan()
    checks.append(check("secret_scan", secrets_ok, secrets_detail))

    forbidden = [str(p.relative_to(ROOT)) for p in iter_source_files()
                 if p.suffix.lower() in {".pt", ".onnx", ".safetensors", ".pem"}
                 or p.name in {".env", ".env.local"}]
    checks.append(check("prohibited_artifact_scan", not forbidden, ", ".join(forbidden) or "none found"))

    passed = all(item["status"] == "passed" for item in checks)
    report = {
        "schema_version": "1.1", "phase": 0, "gate": "PASS" if passed else "FAIL",
        "checks": checks,
        "limitations": [
            "No external dataset, model weights or inference were used.",
            "Scientific performance is not evaluated in Phase 0.",
            "Secret scanning uses conservative pattern matching and is not a substitute for a dedicated repository secret scanner.",
        ],
    }
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
