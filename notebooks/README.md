# Notebooks

## Agri-Intelligence Platform v1

[`Agri_Intelligence_Platform_v1.ipynb`](Agri_Intelligence_Platform_v1.ipynb) is the Google Colab orchestration entry point for the platform workflow.

Current milestone:
- persistent Google Drive layout;
- exact Git branch/commit identity checks;
- runtime dependency discovery without automatic installation;
- resumable Zenodo source recovery for record 15235602;
- size, MD5 and SHA-256 verification;
- source manifest persisted outside the ephemeral Colab filesystem.

The notebook does not train or run inference. Phase 2.5 spatial selection, dataset materialization and evaluation are subsequent milestones implemented through reusable package modules.

Never commit raw datasets, model weights, credentials or user-specific Drive paths.
