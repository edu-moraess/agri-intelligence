#!/usr/bin/env python3
"""Run local, deterministic Phase 0 checks and emit a JSON report."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "phase_0_validation_report.json"

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
    try:
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT, capture_output=True, text=True)
        checks.append(check("structural_tests", result.returncode == 0, (result.stdout + result.stderr).strip()[-2000:]))
    except Exception as exc:
        checks.append(check("structural_tests", False, repr(exc)))
    forbidden = []
    for path in ROOT.rglob("*"):
        if path.is_file() and (path.suffix.lower() in {".pt", ".onnx", ".safetensors"} or path.name in {".env", ".env.local"}):
            forbidden.append(str(path.relative_to(ROOT)))
    checks.append(check("prohibited_artifact_scan", not forbidden, ", ".join(forbidden) or "none found"))
    passed = all(item["status"] == "passed" for item in checks)
    report = {"schema_version": "1.0", "phase": 0, "gate": "PASS" if passed else "FAIL", "checks": checks, "limitations": ["No external dataset, model weights or inference were used.", "Scientific performance is not evaluated in Phase 0."]}
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
