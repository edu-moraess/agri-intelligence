# Agri-Intelligence Platform v1 — Architecture Blueprint

**Status:** architecture baseline for implementation  
**Branch:** `feat/platform-notebook-v1`  
**Base commit:** `0a69c61cd6872d608c57a026cb6ea06500c3ca6b` (`feat/phase-2-4-evaluation`)  
**Owner:** ArqTech Labs

## 1. Mission and product boundary

Agri-Intelligence is a modular agricultural intelligence platform. Its purpose is to ingest, preserve, interpret, correlate and monitor agricultural evidence from imagery, geospatial sources, field sensors, environmental sources and time-series data.

The maize-seedling experiment is the first real perception experiment. It is not the product definition and must not make the platform dependent on maize, YOLO, RGB imagery or one dataset.

The requested "mission-critical / military-grade" standard is translated into engineering properties: deterministic execution, explicit contracts, integrity verification, provenance, bounded resource use, recoverable state, observability, fault containment and auditable outputs. It does not imply military use or a claim of production certification.

## 2. Repository baseline and state reconciliation

The GitHub branch available as the latest confirmed Phase 2 baseline is:

- Branch: `feat/phase-2-4-evaluation`
- Commit: `0a69c61cd6872d608c57a026cb6ea06500c3ca6b`

The previously reported `feat/phase-2-5-first-real-experiment` branch and commit `0cb46c6...` were not found in the remote branch listing. Treat them as local/unpublished state until the user restores or publishes the bundle. Do not claim that the Phase 2.5 protocol and L2 modules are present in this remote base.

The remote tree already contains reusable foundations:
- `core/contracts.py`: evidence and provenance concepts.
- `data/contracts.py`, `annotations.py`, `inventory.py`, `leakage.py`, `manifest.py`, `spatial.py`: dataset governance and audit contracts.
- `perception/contracts.py`, `image_io.py`, `tiling.py`, `postprocessing.py`: model-independent image perception contracts and processing.
- `evaluation/detection.py`: deterministic image-space detection evaluation.
- Existing tests and architecture/roadmap documentation.

Do not duplicate these modules. The new notebook is an orchestration surface, not a second implementation of the platform.

## 3. Architectural layers

1. **Acquisition and provenance** — source registry, source metadata, license evidence, checksums, acquisition time and immutable source references.
2. **Data foundation** — inventory, schema validation, manifests, annotation integrity, split integrity and leakage checks. Reuse Phase 1.
3. **Image and geospatial I/O** — windowed raster reads, CRS/transform metadata, alpha validity, pixel/world coordinate transforms. Raster-specific dependencies remain optional adapters.
4. **Perception** — image/tile contracts, detector adapters, segmentation adapters and post-processing. Model backend is replaceable.
5. **Sensor and environmental ingestion** — typed observations with units, timestamps, sensor identity, calibration metadata and quality flags.
6. **Temporal intelligence** — event/time-series alignment, observation history and change analysis.
7. **Multimodal fusion** — explicit alignment and fusion contracts; never join modalities merely because timestamps or locations look similar.
8. **Agricultural context and analytics** — domain-specific interpretations with evidence, uncertainty and validation status.
9. **Evaluation and model lifecycle** — reproducible runs, frozen test protocols, model/version/checkpoint registry and drift monitoring.
10. **Decision and interface** — maps, reports, APIs, alerts and recommendations. Recommendations require separately validated agronomic rules and must not be inferred directly from detections.

### Evidence promotion rule

Keep these types distinct:
`raw asset -> observation -> model prediction -> derived measurement -> statistical estimate -> agronomic interpretation -> recommendation`.

Each transition must declare its method, inputs, provenance and uncertainty. No automatic promotion from a visual detection to an agronomic diagnosis.

## 4. Notebook and package responsibilities

### Notebook

`notebooks/Agri_Intelligence_Platform_v1.ipynb` is the Colab entry point. It should:
- mount Drive and resolve persistent paths;
- clone or validate the exact repository branch without overwriting a dirty workspace;
- check runtime/dependency compatibility without silent installs;
- recover source data from the authoritative Zenodo record only when absent or invalid;
- verify source sizes and checksums before use;
- orchestrate existing package APIs;
- persist execution state, manifests, logs, reports and checkpoints to Drive;
- display concise stage results and actionable errors.

The notebook must not contain duplicate domain logic or giant monolithic cells. Each cell should represent one functional operation. Required checks for a stage should be grouped into one consolidated gate.

### Python package

Domain logic belongs under `src/agri_intelligence/`, with unit tests under `tests/`. Add a module only when it owns reusable behavior that can be tested independently of Colab.

### Persistent data layer

Drive is the durable artifact store for this Colab workflow, not a relational database. Use immutable source files, versioned derived datasets and atomic JSON state/manifest writes.

Proposed Drive layout:

```text
Agri-Intelligence/
  data/
    raw/zenodo_15235602/
    interim/phase_2_5/
    processed/phase_2_5/<dataset_version>/
  state/
    active_run.json
    checkpoints/
  artifacts/
    manifests/
    metrics/
    reports/
    overlays/
  logs/
```

Raw data must never be committed to Git. Each artifact must have a relative path, size, checksum, source/run ID and creation metadata.

## 5. Phase 2.5 dataset recovery

Authoritative source: Zenodo record `15235602`, DOI `10.5281/zenodo.15235602`.

Primary inputs:
- `orthomosaic_1.tif`, `orthomosaic_2.tif`, `orthomosaic_3.tif`
- `gt_1.shp`, `gt_2.shp`, `gt_3.shp`

A Shapefile is a file family, not a single file. Recover and preserve the corresponding `.shp`, `.shx`, `.dbf`, `.prj`, `.cpg` and available metadata sidecars from the record. Do not assume that the six primary filenames are the entire download set.

The notebook must:
1. query the Zenodo record API and enumerate files;
2. select the three orthomosaics and the three GT Shapefile families only (not `HC_bboxes_*` or `tiles_*`);
3. skip files already present and checksum-valid;
4. stream missing files to a temporary path on Drive;
5. verify the record's file size and MD5 before atomic rename;
6. compute and store SHA-256 for local provenance;
7. write a recovery manifest with the record metadata and exact file links.

Known orthomosaic dimensions, bands, CRS, GSD and checksums are recorded in the project handoff and must be revalidated against the actual files. Read GeoTIFFs by Rasterio windows; never load full mosaics into RAM.

**License evidence:** the Zenodo landing page lists the Rights/License heading but does not visibly expose a license value in the reviewed page. The previous working notes recorded a CC-BY-4.0 decision with a caveat about third-party rights. The notebook must capture the actual API metadata and preserve the caveat; do not fabricate a license field or legal conclusion. A technical download does not itself establish all rights for commercial redistribution.

## 6. Phase 2.5 experiment protocol

Preserve the previously approved protocol as a versioned experiment specification, but reconcile it with the remote branch before execution.

Known protocol decisions:
- global 20 m block grid; IDs `ix_iy`;
- split by spatial block, not by source mosaic or tile;
- 1024 × 1024 px tiles, no overlap, centered in each block and snapped to source pixel grid;
- select overlapping source by highest alpha-valid fraction; tie-break by lowest source ID; minimum 0.995;
- try the alternate source if the preferred source fails; record discarded source;
- seed 42, quotas 86/18/18 for train/validation/test;
- source × median-GT-density stratification with largest-remainder allocation and deterministic SHA-256 ordering;
- Polygon becomes one bbox; MultiPolygon remains one instance using union bounds and records part count;
- partial edge object is included when visible fraction is at least 50%; below 50% is excluded with a disposition;
- alpha-invalid center and degenerate boxes have explicit dispositions;
- every source annotation receives exactly one disposition; conservation per source must match the source counts;
- preserve `gt_master`, write exclusions and tile/split sidecars, and hash every sidecar;
- use existing data, perception and evaluation contracts; add explicit spatial leakage audit because current generic leakage audit does not verify geographic footprint separation.

Training/evaluation protocol remains gated behind successful data preparation. Do not start training in the notebook's initial setup/recovery milestone.

## 7. Execution state and recoverability

Every run records:
- `run_id`, UTC start/end, notebook version and Git branch/commit;
- config JSON and config SHA-256;
- source manifest checksum;
- Python/platform and relevant library versions;
- current stage and stage result;
- artifact paths and hashes;
- warnings, failures and resume metadata.

State transitions must be explicit. A resumed run must verify source/config/artifact hashes before continuing. Never silently reuse a stale artifact after its inputs or config changed.

Use atomic writes for JSON state/manifests. Write large files to `.part` paths and rename only after validation. Keep at least one previous valid state snapshot.

## 8. Resource and failure policy

- No full-raster reads into RAM.
- Prefer Rasterio window reads and chunked file hashing.
- Do not auto-install dependencies or auto-download model weights.
- Do not silently downgrade resolution, alter seeds or relax acceptance criteria.
- Distinguish `BLOCKED`, `FAIL`, `PASS_WITH_WARNINGS` and `PASS`.
- A missing optional dependency should produce an explicit environment block and installation instruction, not a hidden mutation.
- Any failed checksum blocks use of that file.
- A partial download is never considered a valid source asset.

## 9. Implementation sequence

1. Establish a new development branch from the latest confirmed remote Phase 2 baseline.
2. Add this architecture blueprint and the new Colab notebook.
3. Implement Drive bootstrap, repository identity checks, Zenodo recovery and source manifest.
4. Run one consolidated recovery/integrity gate.
5. Reconcile/import the unpublished Phase 2.5 protocol and L2 work from the user's local bundle, if available; otherwise rebuild only the missing code with tests.
6. Implement the spatial selection and materialization flow as tested package modules and notebook orchestration.
7. Build dataset manifest and leakage checks.
8. Only after the data gates pass, execute the approved smoke test, training and evaluation.
9. Keep the multimodal roadmap modular; do not add empty placeholder modules merely to make the tree look complete.

## 10. Explicit non-goals for the first notebook milestone

- No model training or inference.
- No automatic dependency installation.
- No automatic model-weight downloads.
- No raw data in Git.
- No changes to `main`, GitHub Actions or `pyproject.toml`.
- No duplicated Data Engine, perception or evaluation framework.
- No agronomic recommendations from visual detections alone.

## 11. Acceptance criteria for notebook v1 foundation

- Notebook opens as valid nbformat 4.
- It identifies the exact Git branch and commit.
- Drive paths are stable and all outputs are stored outside the ephemeral Colab filesystem.
- Source recovery is resumable and checksum-verified.
- Shapefile sidecars are handled as families.
- Source and local manifests are deterministic and traceable.
- No model training or inference is invoked.
- User-facing output is concise and every result is evidence-backed.
