#!/usr/bin/env python3
"""Build a local JSON inventory; this command never downloads a dataset."""
from __future__ import annotations
import argparse
from datetime import date
from pathlib import Path
from agri_intelligence.data.contracts import DatasetLicense, DatasetManifest, DatasetSource, DatasetVersion, LicenseStatus
from agri_intelligence.data.inventory import inventory_paths
from agri_intelligence.data.manifest import write_manifest

def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory a local dataset directory without loading image payloads.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--version", default="unversioned")
    parser.add_argument("--source-uri", default="local://unverified")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assets = inventory_paths(args.root)
    manifest = DatasetManifest(
        dataset_id=args.dataset_id,
        version=DatasetVersion(args.version),
        source=DatasetSource(args.source_uri, source_type="local", access_date=date.today().isoformat()),
        license=DatasetLicense(None, LicenseStatus.PENDING_REVIEW, notes=("License was not verified by this inventory command.",)),
        assets=assets,
        limitations=("Local inventory only; no dataset was downloaded.", "License remains pending review."),
    )
    write_manifest(manifest, args.output)
    print(f"wrote {len(assets)} assets to {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
