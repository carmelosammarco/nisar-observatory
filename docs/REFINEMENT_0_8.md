# Refinement release 0.8.0

22 October 2026 · workflow execution engine 1.1.0 · scientific contracts 1.1.0.

This release strengthens the existing seven analyses and ordered workflow editor. It does not introduce another environmental detector. Protected satellite inputs and user-provided gallery images are preserved.

## Correctness changes

| Audit finding | Implemented behaviour | Regression evidence |
|---|---|---|
| Cache identity omitted CRS/transform and local source generation | Versioned key includes complete grid, product, source/checksum identity, filesystem generation and reader options. Cached identity and primary-array shape are checked before reuse. Atomic writes use unique temporary files. | CRS, transform, source replacement and malformed-cache tests |
| Requested baseline could silently shrink | Count-based baseline must contain exactly N observations and leave a later observation. Date-based selection uses the declared boundary and must leave a comparison. | Oversized and date-bounded baseline tests |
| Generic binary observations could be called water | Explicit class semantics distinguish water rules from generic conditions. Evolving volcano latest change and repeated change are separate; legacy persistence labels remain meaningful. | Generic GOFF, water, latest/repeated and legacy legend tests |
| P03 could include projected-envelope corners outside the selected rectangle | Geographic cell-centre mask intersects the supplied domain before baseline, smoothing, scoring and area calculation. | Synthetic UTM domain test; protected Timber replay |
| Smoothing differed between elementary and scientific paths | One normalized Gaussian implementation: reflected boundary, at least 30% finite kernel support, missing central cells remain missing. Sigma is metres divided by actual grid spacing. | Edge, sparse-support, missing-centre and cross-path equivalence tests |
| Removing water tracking still performed it | The compiler explicitly enables/disables the operation. Removed tracking is not executed. | A test fails if the omitted tracking kernel is called |

Old cache files are not deleted or trusted under the new key. Clear them explicitly from **Runs** if wanted. Original/subset files and protected Examples are not cache files.

## Guided and editable readiness

Both run paths apply metadata checks before science reads. **Check workflow** shows a compact readiness panel: source count/product, actual grid, exact per-view baseline/later dates, reference requirements, connected-pair diagnostics and estimated grid-array working memory. Bad duplicates, missing dates, disconnected networks, insufficient baselines and unsupported combinations are rejected. Earthquake groups must contain an event-bracketing pair.

This check does not read HDF5 arrays or certify usable native pixels. Channel availability, actual common support, corrections and viewing geometry are verified during reads. The result retains the readiness report. A recipe can be saved without a complete dataset; running requires the inputs.

The default estimated grid-memory budget is **3072 MiB**, configurable with `NISAR_MEMORY_BUDGET_MB` when launching the service. The estimate covers grid arrays and working copies, not full process peak RAM, native windows, HDF5/library buffers or export. Existing native-window limits remain necessary. Reduce source count, area or resolution demands when the check fails.

## Workflow semantics

The ordered editor remains intentionally linear. Elementary operations execute sequentially. Scientific blocks configure the established kernels; some compound operations require coordinated source arrays and geometry. **Choose the opening result map** selects the method map used by any added output transforms. These transforms modify a separately labelled experimental output, not the original findings or dated method maps.

Compatible smoothing, threshold and patch operations can repeat after a method. An internal smoothing/threshold parameter is not overwritten by another operation of the same type later in the workflow. Compound method blocks remain unique, and unit/order checks still reject invalid combinations. Changing a workflow creates a new experiment, even when its inputs match a documented case.

The operator endpoint exposes parameter schemas, execution descriptions and contract versions. Frontend compatibility guidance is advisory; backend validation remains authoritative. A fully general branching/plugin engine and complete removal of duplicated frontend dependency logic are not claimed.

Recipes declaring engine 1.0.0 remain importable. Their declared version is preserved; execution uses 1.1.0 and records that distinction. Historical numeric outputs are not rewritten. Old generic smoothing experiments can change at edges or sparse support under the unified contract: rerun and evaluate rather than assuming bitwise historical equivalence.

## Result interpretation and exports

New results show **How to read this run**: measurement limits, actual record, algorithm version, support and reference interpretation. Each layer includes valid-pixel coverage and explicit class names where appropriate. Missing maps retain an explanation instead of implying zero change.

Result directories are exported to a temporary staging folder and committed atomically after all maps, metadata and any exact workflow JSON have been written. Failures remove only that new temporary output; existing saved folders are not overwritten.

Numeric COG GeoTIFFs now contain a band description, units, available class labels, layer dates and interpretation. Dataset tags record the algorithm/contract versions, observed record, reference meaning and execution fingerprint. These additions do not rescale numeric data. PNG palettes and category styles remain display choices.

The execution fingerprint excludes palette/range/opacity and recipe name. It includes resolved science options, ordered calculations, grid and source identity. For sources without a supplied checksum, cache generation identifies the local source instance; this is not a cross-computer content checksum. Protected examples have their own verified SHA-256 manifests.

## Interface delivery and version control

Local JS/CSS URLs carry content hashes. Launch/release helpers refresh these stamps, and HTML/scripts/styles revalidate so a browser does not retain an older workflow interface against a newer backend. A local Git repository excludes runtime data, environments, archives, release bundles and protected HDF5 inputs; those inputs still need their separate backup. Source history is local; no remote repository or publication is configured.

## Evidence shown in Examples

| Example | What its comparison supports | What it does not establish |
|---|---|---|
| Mozambique | Qualitative comparison with NASA’s matching-date visualization | Pixel accuracy, depth, recovery from two dates |
| Wheeler Marsh | Historical paper-inspired method applied to new NISAR observations, with tide context | Inherited PALSAR accuracy or continuous hydroperiod |
| Timber Fire | Quantitative single-case comparison with published results and an official boundary | Universal burn classification, burn severity, independent pixel truth from a perimeter alone |
| Mexico City | Relative LOS spatial/rate comparison with NASA | Direct vertical subsidence accuracy or independent closure from a tree network |
| Venezuela | Event-bracketing LOS coverage and qualitative NASA comparison | Uniform physical displacement component across viewing geometries or damage |
| Krasheninnikov | Radar surface-change diary beside NASA morphology frames | Validated lava/snow/wetness separation |
| Samudra Tapu | Published flow-pattern/range comparison with an explicit constrained horizontal estimate | Time-matched independent velocity accuracy or unconstrained 3D motion |

Input verification, numerical replay, published visual comparison and independent scientific accuracy are distinct. The cards and tutorials now identify their comparison scope explicitly.

## Verification

The protected-input replay compares the guided and editable kernels on all seven cases, all 31 inputs and **251 numeric maps**, including missing-value masks. It also checks the recorded historical case metrics separately. All historical metrics remained within their recorded replay tolerances in this release. This equivalence does not establish external accuracy.

- [Machine-readable release verification](validation/refinement-0.8.0.json)
- [Per-case numerical replay receipts](validation/workflows/seven-examples/)
- [Current validation record](VALIDATION.md)
- Regression tests: `tests/test_refinement.py` and the frontend workflow tests.

## Work that still requires new evidence

The software corrections above are implemented. The following research and larger engineering tasks remain separate work, rather than completed validation claims:

1. Independent held-out events/regions, with parameters fixed before inspection, for flood, wetland and fire classification. Use spatial holdouts and report coverage, precision/recall/IoU and boundary uncertainty.
2. Time-, support- and geometry-matched independent motion references for P04/P05/P07. Map agreement and similar maximum values are insufficient; report bias/MAE/RMSE on justified matched samples.
3. Independently dated lava boundaries or complementary observations to attribute P06 scattering changes. No brightness-only change can certify lava.
4. Calibrated uncertainty models for correlated pair errors, atmosphere, reference motion and glacier vertical/terrain assumptions. Sensitivity scenarios remain sensitivity, not confidence intervals.
5. A novice-user study and physical mobile-device testing. Browser checks and logic tests do not measure scientific understanding or replace device testing.
6. Chunked/lazy execution for large cubes, full intermediate previews, a complete shared frontend/backend dependency registry and optional branches. Current execution remains bounded in memory.
7. Public multi-user deployment: app authentication, isolated Earthdata sessions/storage, durable jobs, quotas and hosting security. Current server remains a trusted local single-user service.

No new remote downloads or new independent field observations are part of this refinement. Existing official guides, study links, reference boundaries and protected inputs remain available.


## Transfer, usability and demonstration review · 0.8.15

Earlier validation working material (moved outside this project by its owner) recorded the approved Lucas Fire / Bang Pakong evaluations, unchanged protected replay, concrete usability fixes and recording-ready demonstration package. The fresh release gate passed 734 Python and 284 frontend tests, 502 original numeric-map comparisons and 655 previews. Optional tracking limits now produce explicit diagnostic unavailability without blocking P01/P02/P06 core maps. A completed edited introduction is available in About. No independent novice study, universal environmental accuracy, continuous live recording or new protected Example is claimed.
