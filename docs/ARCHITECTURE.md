# Service structure

```mermaid
flowchart LR
  A[Draw area and choose dates] --> B[Public CMR discovery]
  B --> C[Review compatible source groups]
  C --> D[RAM-only Earthdata session]
  C --> E[Import originals or native area HDF5 files]
  D --> F[Bounded range reader or full download]
  E --> G[Geocoded native-window adapter]
  F --> G
  G --> H[Native quality then product-specific equal-area grids]
  H --> I[Reusable per-area array cache]
  I --> E4[GCOV, GUNW and GOFF calculations]
  E4 --> J[Seven focused experiences]
  I --> W[Editable scientific blocks and elementary operations]
  W --> J
  J --> K[Numeric COG plus preview and provenance]
  K --> L[Linked map, dates, charts, pixel values and interpretation]
```

## Modules

- `catalog.py`: input bounds validation, product collection discovery, asset URL allowlist, filename compatibility groups.
- `access.py`: domain-scoped Earthdata authentication, RAM session lifecycle, HTTP block reader with a transfer ceiling, atomic full downloads and cancellation.
- `subset_storage.py`: product/UTC batch folders, bounded path resolution, recursive discovery and legacy layout support.
- `subsets.py`: bounded native-grid extraction with embedded portable provenance and JSON sidecars.
- `subset_import.py`: self-contained HDF5 area recognition, source/bounds validation, content-based duplicate import detection and managed storage.
- `science.py`: supported HDF5 array inventory and path selection, geocoded native-window reads, equal-area reprojection, quality rules, parameter-keyed array cache.
- `engines.py`: shared GCOV evidence, fixed-reference phase conversion and pair-network diagnostics, configurable offset filtering and common support.
- `processors.py`: seven focused exploratory methods backed by shared and specialized scientific kernels, observation requirements, provenance and interpretation notes.
- `workflows.py`: declarative recipe validation, bounded local execution, named personal tools and portable recipe endpoints.
- `workflow_templates.py`: typed scientific-block dependencies compiled to the established kernels, optional input/output transformations and exact protected-example recipes.
- `examples.py`: checksummed protected inputs, illustrated tutorials and case-specific setup; separate from ordinary user storage.
- `exports.py`: numeric COGs, Web Mercator PNG previews, display scales and result manifests.
- `app.py`: local FastAPI routes, safe imports, jobs/progress/cancellation, saved results, HDF5 inspection and numeric map-pixel access.
- `frontend/`: a buildless browser interface. The scientific algorithms remain server-side; credentials are never embedded in client assets.

## Data contracts

Catalog observations include product, granule ID, original filename, acquisition/pair start/end, source size, approved URL and compatibility group. A run records the bounding rectangle, selected source IDs, project IDs and analysis parameters.

A processor receives aligned arrays, exact sources, array paths, quality paths, units/attributes, grid definition and options. It returns numeric layers, summaries, dated series, interpretation notes and source provenance. The exporter replaces in-memory arrays with downloadable artifact links. Missing numeric values remain missing rather than becoming zero.

## Operational behavior

Only one transfer/processing job runs at a time. Long reads do not block ordinary interface navigation. Cancellation is checked between chunks and stages; the current HTTP read may finish first. Failed downloads remove their partial file. Saved completed results remain readable after restart; interrupted jobs are labeled interrupted.

Data is deliberately bounded for a local prototype. Large global mosaics, unbounded time series and custom raw-SAR processing require different execution/storage infrastructure. This release uses a local JSON job store and one worker; a public multi-user service would require authentication, isolated credentials, quotas and a durable queue.


## Guided inputs and interactive display · 0.1.2

`frontend/experience.js` implements the next-run checklist, reference/external-input dialog and observation playback. `app.js` renders numeric layers through `/api/visualization/{job}/{project}/{layer}` and guards against stale responses. The endpoint validates result/layer identifiers against the saved manifest, reads only bounded rasters, generates display-only PNGs, and exposes range, clipping and constant-value information. Numeric artifacts remain unchanged. Dated frame responses are cached in the browser for the current result. Active processors export available acquired-date or interval frames for GCOV, GUNW and GOFF. Legacy moisture readers are separate from the active tool catalogue.

Full-original downloads no longer have an eight-file count cap. They remain sequential under the single-worker queue, with cancellation and an 8 GiB per-file safeguard. Current discovery paginates up to 5,000 records per product and explicitly identifies its selected BETA or provisional V1 collection; analyses accept at most 32 sources. These are distinct limits.


## Workspace lifecycle and saved originals · 0.1.3

Explore startup fetches local availability into a separate inventory without populating the catalog. Use saved data explicitly restores area/date-matching originals and covering native extracts, including product/time folders and legacy flat storage. Public discovery matches exact saved filenames and retains catalog identity alongside the local record ID, so imported originals can be reused without a network transfer. Download requests reject fully existing selections and filter existing or repeated records from mixed batches before worker submission.

Client-side reset increments request generations, stops UI polling/playback, clears the area/catalog/result and resets settings; it makes no delete or cancellation request. Server jobs and stored artifacts remain intact. The observation table maintains independent analysis and download selections.

The result navigator separates explained summary maps from dated observations. Playback uses one loaded image at a time, stops at the end by default, supports opt-in looping and direct date selection, and swaps the overlay only after the new image load completes. Pausing or changing selection invalidates pending preview responses. Numeric exports remain unchanged.


## Scientific processing maturity 0.2.0

The native adapter screens invalid values before averaging; recognized quality companions must match the science layer native grid. Accepted native counts, fractions and source spacing are recorded. Minimum accepted native support is configurable, default 50%. Reader version is part of the cache key, so the corrected adapter bypasses historical arrays without deleting them.

The worker reads only products needed by the requested tools and creates an independent grid per product. Fixed common support drives regional trajectories, water-area accounting and audio. Phase references require identical valid physical cells across every pair, plus comparison support outside the reference. Empty intersections fail with actionable messages.

Each new result contains a deterministic `report` with numeric observations and interpretation limits, plus `extra.support` and product-specific diagnostic tables. These are calculated locally without a language-model or external summary service. The interface preserves legacy exports, labels historical calculations and provides per-layer explanations and exact source/version provenance.

See [current processing methods](PROCESSING.md) and [current verification](VALIDATION.md). Historical design files are retained as background; the interface loads only the current implemented tool registry, `docs/tools.json`.


## Processing and current tool guides · 0.3.0

- `spatial.py` validates named study/reference/label polygons and tracks dated connected candidates with physical-area thresholds, overlap links, splits and merges.
- `validation.py` separates training labels from held-out evaluation and calculates matched regional-reference errors. Supplied provenance does not itself establish independence.
- `advanced.py` implements robust baselines, grid sensitivity, local offset screening and conditionally identifiable phase-network/annual models.
- Native contribution and rejection planes travel with cached science arrays and export as diagnostic maps. Optional cross-polarization, soil-method and explicitly requested delivered ionosphere-screen reads retain their source paths.
- `docs/tools.json` drives the seven tool cards and current method pages. The current mission chapters are maintained in `docs/mission.json`.

The local single-worker service remains the deployment model. It does not automatically correct three-dimensional tropospheric/tidal lookup tables or establish independent environmental accuracy. Historical release notes above describe their respective releases.


### P04 rate integration (0.4.0)

`backend/los.py` reuses the chronological incidence solver with an explicit connected-tree allowance for P04, then fits intercept + slope at acquired epochs. Other phase tools retain their redundant-cycle gate. Original pair arrays and reference validation in mm are retained alongside rate/cumulative products. `phase_allow_mixed_revisions` is explicit, scoped to P04-only requests, and normalizes revision digits while retaining release-family and viewing-geometry identifiers. Native reader/cache version remains 0.3.0; algorithm version is 0.4.0. GUNW runs containing P04 allow up to 900 grid cells per axis; other grids retain 384. Local originals are preferred without authentication and are never deleted by processing.


### Shared reference assistant and palette controls (application 0.4.4)

`POST /api/reference-assistant` queues a `reference` job on the existing single worker using a typed single-tool request for P03, P04 or P05, authentication boundaries and local-original preference. Failed source reads stop the assessment rather than silently recommending a reference for a smaller source set. Candidate evidence is persisted as `{project}/reference_assistant.json` and reopened through the normal artifact route. The assistant shares the normal queue, cancellation and run history; it is not a separate unbounded request loop.

`frontend/reference-assistant.js` handles the candidate cards, bounded map outlines, explicit adoption, stale-context guards and opt-in restoration of saved local inputs. Adopted provenance is verified on the server and copied into the analysis job. Changing area clears candidate outlines/working assessment; saved evidence remains intact.

The visualization endpoint accepts `palette=standard|mexico` and `mode=shared|robust|full|custom|mexico`. Display choice is part of the browser preview-cache key. Inapplicable Mexico palette/range requests have explicit fallback notes; class semantics and numeric exports remain fixed. Release 0.4.1 changes suitability assistance and presentation; P04 motion algorithm remains 0.4.0.


### Curated result navigation and P04 display units

`frontend/result-views.js` assigns saved outputs to Main results, Explore time, Quality & reliability and Advanced maps, with a complete download library. `experience.js` handles section controls and explanations. The registry is presentation-only: all saved rasters and scientific computations are preserved. Historical outputs fall back to available measurements rather than creating new layers. P04 selects its existing annual or monthly rate raster, converts custom display endpoints by 12 and synchronizes preview and export links. Accumulated-change frames retain cm units. Frontend tests cover all seven actual processor-output inventories generated from synthetic observations, plus integrated preview/export navigation.


### P05 earthquake interval and coverage mosaic · 0.4.2

`backend/quake.py` checks strict event timing, validates adjacent same-direction groups and assembles independently referenced P05 results. `processors.py` retains original pair maps and adds the primary cm map. A `quake_mosaic` request is P05-only; its support is a spatial union with explicit source indices and per-group references, rather than a global time-series footprint. Workers stop P05 when any selected GUNW source fails to read. P05 shares the bounded 900-cell-per-axis GUNW grid limit with P04. `frontend/quake-workflow.js` provides explicit multi-group selection and the guided NASA example. The preview and PNG renderer share the earthquake palette/range; standard/rainbow P04 controls remain separate.


### Shared numeric display and native-mask correction · 0.4.3

`sharedDisplayPalettes` in `experience.js` is the single visible palette registry for all seven tools. Server `rainbow` and `diverging` options apply to numeric layers across products; legacy `mexico`/`quake` API values remain compatible but are absent from visible controls. Range controls are shared; Custom carries fixed endpoints in the active units. Reader version 0.3.1 decodes GUNW packed masks before aggregation and invalidates old cache keys. The P05 mosaic passes an internal reference mask to the ordinary phase engine when at least 25 valid reference cells are shared across all groups. It does not fit event pixels, ramps or offsets to the published map.

`processing_grid` is shared by the normal worker and assistant worker. Reference assistant 2.0 uses bounded coverage-seeded windows at multiple sizes, product-specific comparison units and project/version-aware fingerprints. A P05 event-coverage assessment permits duplicate intervals across different validated frames and uses each group’s union for comparison-ground checks. Candidate support itself remains shared across all selected sources. GCOV baseline departures match the P03 processor. Selected-candidate evidence retains comparison units and source order when copied into results. See [the shared reference guide](REFERENCE_ASSISTANT.md).

## Maintenance and release contents

Release packages include Recipes and optionally protected example HDF5 inputs. They exclude personal runtime data, installed environments, bytecode/test caches and the optional archive. The offline workflow replay remains usable after historical saved runs have been deleted: it compares the protected inputs directly, reports unavailable historical exports explicitly, and still fails for a partial or numerically changed saved export.

## Shared contracts and durable runtime

Scientific option models live in `analysis_options.py`; display models live in `display_settings.py`. Recipe validation imports these modules without initializing the web service. Editable block limits reuse authoritative shared fields, so the editor and runtime agree on supported values.

Readiness follows temporal domains: a connected pair network creates acquisition epochs, so later baseline requirements count those epochs rather than input pair files. Explicit Flood Memory comparison dates list all pre-comparison baseline acquisitions separately from the general context baseline. Baseline-subtracted reconstructed dates retain a distinct `processed_epoch` label and do not claim that the first date stays zero.

`runtime_storage.py` gives one process ownership of each runtime directory, supports separate local storage roots, durably writes job records and explicitly recovers unfinished work. The FastAPI lifespan holds the lease through worker shutdown. Import-time metadata loading is read-only. This does not implement a distributed queue, public authentication or separate-user hosting.

## Free-space budgets and offline snapshots · 0.8.2

`storage_budget.py` checks the destination filesystem and a configurable free-space floor. Transfers check known content length before writing and recheck each chunk. Area extraction checks planned native science bytes plus metadata/geometry overhead; geometry and cache/export writers recheck their actual array sizes. Readiness reports free disk space without suggesting that it is a guaranteed reservation.

`newjob` persists the complete initial request before publishing the job in RAM. `submit_job` wraps all worker kinds, marks an unexpectedly stopped worker terminal and keeps the queue available even if final persistence fails. A later restart still recovers whatever unfinished metadata was last committed. Completed earlier outputs are retained.

`workspace_backup.py` operates offline under the same runtime lease. Its allowlist includes raw, subsets, jobs, workflows and optional arrays. ZIP members carry a SHA-256 manifest and bounded sizes. Restore validates the entire archive before creating its destination, stages and rechecks each file, and publishes to an exclusively created fresh directory under a lease. A durable incomplete marker blocks app startup after an interrupted publication. Source code, protected examples and RAM sessions are outside the runtime snapshot.

## Single workflow contract · 0.8.3

`workflow_contract.py` defines declarative elementary transitions, common prerequisites, scientific family grammars, optional internal stages, output filters, post-transform rules and minimum-source calculations. `workflow_parameters.py` supplies typed schemas/defaults; shared bounds come from `analysis_options.py`. `workflow_templates.py` binds a validated plan to the existing scientific kernels without a second order grammar. The browser's `workflow-contract.js` is a small interpreter for the server-published rules; `workflow-workspace.js` presents the controls and human guidance. Recipes cannot supply rule expressions or executable code.

`GET /api/workflow-operators` publishes rules, parameter schemas/defaults, operator descriptions and available method outputs. `POST /api/workflows/inspect` inspects an incomplete or complete typed draft without opening satellite data. Inspection reports primary input/output units, temporal domains, insertion requirements, available maps and minimum source counts. Scientific blocks can also generate other maps/diagnostics; their primary typed flow does not imply that every internal calculation has a separately saved raster.

The rule bundle is identified by version and SHA-256 in new result JSON and GeoTIFF tags. Existing saved outputs are not rewritten. A frozen acceptance fixture from commit `8acbe66` independently preserves 0.8.2 canonical recipe acceptance; a generated cross-language corpus checks Python/browser agreement. Export the browser test fixture with `scripts/export_workflow_fixture.py` after intentional rule/schema changes and review the compatibility evidence rather than blindly refreshing acceptance baselines.


## Cooperative cancellation and bounded export rendering · 0.8.4

`backend/execution.py` scopes the owning job’s cancellation callback with a `ContextVar`. Every submitted worker enters that scope and resets it even on failure; callbacks do not leak into later jobs or other threads. `ProcessingCancelled` is a `BaseException` control signal, deliberately outside data-error handlers. The supervisor catches it and records a terminal cancelled job without replacing earlier results. Source-error handlers also recheck cancellation when a native I/O library wraps an error. Direct Python callers can explicitly catch `ProcessingCancelled` when supplying cancellation callbacks.

Shared scientific kernels retain their arithmetic and solver order. Entry/exit, per-stage/date/view and reference-search checkpoints allow cooperative stopping; an indivisible NumPy/SciPy/GDAL call is not forcibly interrupted. Source reads and cache publication check their explicit callback. New cache/export temporary files are removed on cancellation; committed caches, source files and completed bundles remain. Export checks cancellation before atomic publication. A cancellation arriving after publication does not retract a complete bundle.

`exports.colorize` retains exact finite-value global percentiles, interpolation, category overrides and alpha semantics from the frozen 0.8.3 renderer. C-order buffered iteration bounds interpolation/RGB temporaries to 65,536 pixels even for transposed inputs; the input, global percentile vector and final RGBA image remain resident. COG creation writes native tile windows and is tested across tile boundaries. This is bounded rendering/export I/O, not a lazy scientific stack or a guaranteed whole-process memory bound. `scripts/verify_render_memory.py` measures fresh-process peak RSS on macOS/Linux and checks exact output hash/range against the frozen renderer.


## Executed-step evidence · 0.8.5

`processing_trace.py` scopes an optional collector to a new custom/editable workflow. Kernels emit actual intermediate arrays at selected boundaries: GCOV baselines, pre-patch thresholds, event-selected input phase and pre-normalization/bias/geometry offset evidence. No second scientific processing pass is used to reconstruct a hidden stage. Derived threshold snapshots apply the same declared rule to the actual score/departure consumed by patch filtering. Original calculations, map IDs, metrics and timelines remain unchanged.

Existing outputs are associated with their executed blocks by references, rather than copied. A collector keeps only the latest snapshot per operation/key/view and copies arrays before later in-place arithmetic can mutate them. Context reset, thread isolation, shape validation, safe map identifiers and group-hash collision rejection prevent cross-run contamination or silent replacement. Elementary steps link their already saved latest/baseline/residual maps. Method snapshots are float32, consistent with numeric result exports. They retain actual units, available dates and their view label; whole-run input lineage remains in the result record. This is selected-boundary inspection, not arbitrary branching, all intermediate dates, or a complete internal debugger.

`extra.processing_trace` version 1.0.0 lists stage indices/operations, captured versus existing map roles, actual map units and diagnostic keys. Scientific blocks configure fused kernels: a rate diagnostic can differ from the plan's abstract displacement I/O. The browser explains this distinction. Optional post-transforms link their own `workflow_post_*` maps rather than an internal operation with the same name. Metadata-only readiness adds a conservative float32 snapshot allowance to its working-grid estimate. Export includes intermediate maps in the same atomic bundle; COG band tags identify the processing stage/group. The execution fingerprint still describes the scientific input/plan rather than presentation or tracing metadata.

`processingTraceHTML` presents numbered cards with the shared parameter titles/visibility, bounded advanced diagnostic previews and direct map buttons. `mountProcessingTrace` reuses the normal map viewer/navigation and export controls, and ignores clicks after another result replaces the current result. Snapshot quantities have distinct custom-range identities. Original guided and historical results retain their existing presentation. The seven protected replays check every trace map link/unit/shape as well as the original 251 numeric-map equivalence checks.


## Exact shared display ranges · 0.8.6

`display_range.raster_percentiles` keeps peer datasets open and reads windows no larger than 256 × 256 cells. It preserves the existing observation-peer grouping and percentile definitions. Small populations (up to 262,144 finite values) use NumPy directly. Larger populations count ordered IEEE float-key bytes and refine just the needed order statistics over four float32/eight float64 passes. Interpolation retains the pinned NumPy linear-percentile arithmetic, including float32 subtraction and the upper-end branch. Common dtype promotion follows the source rasters. Saved outputs are float32; float64/mixed-float inputs are also covered.

No sample quantiles, approximate bins, persistent range cache or scratch science files are created. Source datasets close on completion/error/cancellation. Cooperative cancellation is checked per window/pass. A disappeared selected rank is rejected rather than returning a fabricated range. Raster handles remain open through the passes; application result bundles are immutable apart from display JSON metadata. The viewer maps missing/unreadable peer files to a clear retry message.

This bounds the range algorithm's Python/NumPy buffers, not GDAL's cache, the selected map, reprojection, PNG output, concurrent requests or scientific observation stacks. More reads can cost time on slow drives; no universal speedup or process-memory cap is claimed. `verify_shared_range_memory.py` isolates range RSS; `verify_saved_shared_ranges.py` compares complete saved-preview responses against the previous concatenated implementation without modifying the run files.


## Preview/PNG admission and browser cache · 0.8.7

`RenderAdmission` wraps both heavy display endpoints. One nonblocking semaphore slot bounds simultaneous expensive render functions. The PNG route may call the visualization resolver using its owning thread's scoped context; copied contexts on other threads cannot bypass admission. `finally` resets ownership and releases the slot after ordinary exceptions or cooperative cancellation. Busy requests return HTTP 429 with `Retry-After: 1` and `X-NISAR-Render-Busy: 1`, before reading the rasters. They do not occupy a queued render slot. Health/control APIs and raw numeric downloads do not use this gate.

`render-requests.js` retries only this marked admission response, with a one-minute admission-wait deadline. It does not retry mutations, other 429s, ordinary validation failures or provider failures. Starting another preview aborts the older fetch/wait, while version checks still protect overlay/cache state. A running native server call can finish after browser cancellation; the semaphore remains owned by its synchronous worker until it exits. PNG and previews share admission, avoiding parallel copies of their large intermediate arrays.

The browser's LRU preview cache has at most 24 entries and 32 MiB of conservative estimated encoded-image/metadata storage. Oversized maps are displayed without retention; clearMapResult clears the cache. This is not a browser heap quota: native decoded images, current responses, PNG blobs and other application objects also consume memory. Likewise, admission bounds expensive functions, not response transmission, all ASGI/thread memory, GDAL caches or concurrent scientific processing. There is no separate-user queue or general process-memory guarantee.

Evidence combines deterministic concurrency/failure/context tests, real frontend request/cache wiring tests, a read-only 12-request live burst, exact sequential response hashes before/after, and browser playback/export checks. `scripts/verify_render_admission.py` is repeatable against a loopback app with a saved P03 result, without creating a run or downloading satellite files.

`map-download.js` keeps the originally requested PNG URL/filename while a user changes maps or opens another run. Busy-state and completion/error messages update the current panel, distinguishing the previous export from the displayed map. Both the original and replacement button are released on completion/failure; availability rules are retained. Deterministic frontend tests cover a replaced result panel during successful and failed exports.


## Regional reference quantity contract · 0.8.8

`RegionalReference` types the optional quantity/unit/component fields and ordered pair dates. `validation.regional_reference_spec` supplies the shared semantic checks for readiness and processing: product/solution/component compatibility, explicit interval identity, finite values, dimension-preserving unit conversion, nonnegative speed and duplicate-record rejection. The wrapper `regional_validation` selects the named series; the horizontal processor retains its signed radar-component series separately. Reports record the quantity's own common-support count/area, rather than borrowing another quantity's support.

`continuous_validation` matches UTC calendar dates to exactly one observed pair, computes app-minus-reference errors and records each matched or excluded interval. Missing summaries are never zero residuals or silently omitted records. No-reference runs retain the existing not-evaluated record and do not change scientific maps/metrics/series. Legacy assumptions are disclosed for phase/radar-mode records, while ambiguous horizontal records fail closed. This is a reference-check schema/reporting refinement; the scientific kernel/engine versions are unchanged.

The result UI names the quantity/component/units, shows scientific small values without rounding them to false zeros, explains the regional-median basis, and previews at most 20 matched records with escaped citations. Full data/conversions remain in the run JSON. Settings and INPUTS.md provide the same quantity choices and limitations. Readiness rejects references for multi-group earthquake mosaics or elementary transformed workflows without an appropriate evaluator.

Regional error summaries scale residuals before RMS/mean arithmetic to avoid overflow from squaring large finite errors or underflowing tiny nonzero errors into a false zero. Nonrepresentable differences/statistics are rejected explicitly. This changes only supplied-reference error arithmetic, not NISAR maps or their regional measurements.


## Study-domain and auxiliary-footprint contract · 0.8.9

The guided processor distinguishes the study domain, a method-consumed processing footprint and source diagnostics. Only GUNW/reference-based GCOV retain the actual selected reference; irrelevant stable/reference roles do not enlarge unrelated measurements. Common study coverage must exist, and the shared phase engine separately requires comparison cells inside the study outside its reference. A valid reference outside the study is retained for normalization. GCOV common summaries, phase comparisons and scientific measurement maps use the study mask.

Both GOFF components are masked to the same processing footprint before filtering. Local/global spatial filter populations are restricted to the study domain; auxiliary stable samples outside it retain native-quality screening for their median bias diagnostic/correction. Raw offset/ratio diagnostics retain their explicitly labelled source/processing support. Quality and reference-support rasters are also diagnostic exceptions to the measurement mask.

Elementary workflows use `spatial.role_mask` to rasterize only needed role unions without retaining per-feature masks. They preserve phase references until LOS conversion, then restrict subsequent calculations, network fits, summaries and maps to the study domain. Shared context survives recipe collection/import/export; the settings page explains which roles are operative versus annotations.

New domain runs record `extra.spatial_support.version = 1.0`, geometry-mask counts and the auxiliary policy. The spatial-contract version enters the scientific execution fingerprint. GeoTIFFs carry spatial scope/version tags; the map explanation distinguishes study measurements from diagnostics. A targeted historical-domain notice avoids flagging already-correct, unfiltered/clipped example paths. This is a processing-boundary correction, not new independent environmental validation or a change to the default analysis-grid/bounding-box convention.


## Shared resource admission · 0.8.10

`backend/resource_budget.py` owns the existing resident-grid estimate, intermediate-snapshot allowance, configured memory threshold and destination-disk safety check. `readiness.assess` reuses it for guided and editable analyses. The reference-assistant route checks it before `newjob` and the worker checks again before loading any source, retaining the report in its job/result JSON. The direct assistant kernel checks before stacking arrays. A candidate-selection operation does not need a pre-existing reference, baseline or phase network; resource admission is separate from those scientific requirements.

Invalid `NISAR_MEMORY_BUDGET_MB` fails startup before acquiring the runtime lease. Passing admission does not reserve OS memory/disk or bound native/library/export overhead. Whole-process quotas and end-to-end memory stress coverage remain separate work; the estimate and default 3072 MiB have not been loosened.


## Shared keyboard navigation · 0.8.11

`frontend/page-navigation.js` owns visible-heading focus, page titles, current sidebar-section semantics and the skip link. It changes DOM navigation only, without touching map bounds, recipes or saved results. Same-page background updates do not steal focus. Settings subpages keep Explore as their current section; tutorials use their case title and return focus to the index on Back. Native tool buttons keep focus through list re-rendering and announce their selected state.

Explicit sidebar/brand navigation cancels pending tutorial preparation. The cancellation token is not invalidated by the tutorial’s own internal workspace preparation. Shared navigation scrolling respects reduced motion; CSS also limits transitions/animations when that preference is active. Existing other map/plot transitions are outside this specific claim. The map has a named region and a coordinate-entry alternative to mouse drawing. Help, source inventory and catalog dialogs have explicit heading labels.

The design follows [W3C focus-order guidance](https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html), the [skip-link technique](https://www.w3.org/WAI/WCAG21/Techniques/general/G1) and [contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum). Current engineering evidence is limited to the paths and text pairs in [keyboard-navigation.json](validation/keyboard-navigation.json); full accessibility and novice-user evaluation remain open.


## Bounded geometry interpolation · 0.8.12

`backend/glacier_geometry.py` now separates native-format version `goff-geometry-1` from interpolation-adapter version `goff-geometry-2`. Validated axis metadata and bounded target-point passes establish the exact native window before any 3D field is read. Two bracketing height planes preserve the old interpolant’s right-interval choice at internal exact samples, including zero-weight NaN neighbours. Five retained float64 fields share a 64 MiB allowance. Interpolation batches are at most 65,536 points and have cooperative cancellation boundaries. Affine row/column vectors are both used.

Per-axis metadata is limited to one million samples; target grids have at most 2048 cells per side and 4 million cells; a source HDF5 chunk larger than 64 MiB is rejected before native decoding. No-overlap targets remain missing without science-cube reads. New horizontal-only cache keys include the adapter version, preserving all other cache identities and old files.

The fresh-process synthetic comparison uses sparse fill-valued HDF5 cubes to measure allocation paths, not real I/O throughput. Peak RSS measured 488,669,184 bytes for the former full-cube path and 137,068,544 bytes for the bounded path, with exact output hashes. These are geometry-only results, excluding the rest of the scientific job. [Memory receipt](validation/geometry-window-memory.json) · [Real-data/oracle evidence](validation/geometry-windowing.json).


## Durable ordinary metadata · 0.8.13

My Tools and reference-assistant reports use `guarded_json`: destination free-space admission, a unique temporary file, file flush/fsync, atomic replacement and directory fsync where supported. Ordinary metadata respects the safety reserve; emergency terminal-job records retain their separate durable write path. A save failure after replacement can leave the complete new file present, so the API returns an actionable 507 without claiming that the old value survived. Reference report storage failures do not claim a completed assessment or misdiagnose source schema. Release ZIP hashing streams file contents rather than reading the complete bundle into RAM.


## Shared result interpretation · 0.8.14

`docs/tools.json` contains versioned reading guides and mode variants. `result_contracts.reading_guide` resolves the actual method/mode, including scientific editable workflows, and exports the interpretation without changing numerical identity or rasters. Frontend result guides use this saved text, or the same tool guide as a fallback for older runs; all six questions include actual source dates, cell spacing and recorded findings. Elementary experiments do not inherit a case’s accuracy.

`comparison_review` in each example defines reference versus app quantities, support, agreement, differences, unverified claims and next evidence. `frontend/examples.js` renders these beside the existing publisher/app images and a seven-case overview; three tutorial shortcuts express the reviewed demonstration sequence. `scripts/review_example_evidence.py` reuses the isolated full replay and independently evaluates exported fire scores/candidates against archived reference vectors with explicit support and reference hashes. It never mutates personal runs or downloads science data.
