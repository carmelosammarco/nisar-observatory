# Current release · 0.9.0

The delivery target remains a trusted local, single-user research app. Guided discovery now coexists with the scientific laboratory: seven protected recorded studies, new saved runs, controlled experiments, compatible side-by-side comparisons and self-contained study reports. [Current acceptance and evidence](SCENARIO_B.md) · [User guide](STUDY_GUIDE.md).

This release does not provide public hosting, independent beginner sessions, universal environmental accuracy or a guarantee of operational/competition suitability. Earlier release sections below are historical evidence, not current test counts. Code is licensed under MIT; third-party scientific/media rights remain separate. No public repository has been published by this work.

---

# Local research release and future work

On 22 October 2026 the user confirmed the delivery target: **a local, single-user research app**, with possible separate-user hosting later. Docker is deferred. The original broader readiness ledger is narrowed by this explicit decision, not by treating unfinished hosting or scientific research as completed.

The acceptance target is reliable local processing with explicit units, dates, references, support and limitations; reproducible examples and editable workflows; durable storage and recovery; bounded/admitted operations; usable navigation; and a verified install/release. It is not a claim of universal detection accuracy or a guarantee against every hardware/storage failure.

| Local release requirement | Evidence and boundary |
|---|---|
| Seven guided tools and editable example recipes | Known-value/adversarial regression plus protected-case API replay; compare original numeric maps, metrics, dated series and every saved preview. See [release integration](validation/release-integration.json). |
| Shared settings and scientific contracts | Authoritative typed rules serve editor, validator and runtime; 3,528 canonical workflow compatibility cases, explicit domain/reference/unit/interval checks and executed-step inspection. |
| Durable files and runs | Per-runtime OS lease, atomic job records, interrupted-run recovery, checksummed backup/restore, disk admission and atomic My Tools/reference-report saves. Failure messages distinguish an unconfirmed commit from a rejected save. |
| Resource safeguards | Bounded grid/native geometry/render paths, approximate memory/disk admission, one analysis worker and one expensive render at a time. These are safeguards, not an OS memory quota; larger scientific stacks remain in RAM. |
| Interface clarity | Seven-tab/settings/result browser checks, keyboard/focus/dialog checks and sampled text contrast; unavailable maps explain why. No full accessibility or novice-usability certification is claimed. |
| Reproducible local delivery | Pinned fresh Python installation, isolated API/restart gate and a checksummed release including the protected examples. Current native verification is macOS; other operating systems need native acceptance tests. |
| Honest scientific documentation | Tutorials distinguish reproduced measurements from independent validation, and state attribution/reference/geometry limits. Existing case agreement does not establish transfer accuracy elsewhere. |

## Explicit future work

These items remain open and are **not presented as completed**:

- Independent held-out cases and broader uncertainty/sensitivity/transfer studies; especially lava attribution versus snow/wetness, wetland tidal interpretation and motion assumptions.
- Arbitrary internal-stage/date inspection beyond the recorded scientific block outputs, and broader reusable operator coverage.
- Lazy scientific stacks, whole-pipeline stress tests on larger workloads and enforceable process-memory quotas.
- Responsive-device, screen-reader and novice-user task studies; native Windows/Linux delivery acceptance.
- Public/multi-user deployment: application authentication, isolated Earthdata sessions/files/runs, durable multi-user queue, quotas and TLS. The current loopback app must not be advertised as a shared service.
- Docker, desktop installers and hosted deployment, only when separately requested.

The historical sections below retain the evidence and unfinished scope as recorded at each release. References there to separate-user hosting as a release requirement predate the user's local-only clarification above.

## Completed local hardening · 0.8.1

- Unified shared option models and editable block parameter limits.
- Corrected readiness checks to follow acquisition versus reconstructed-epoch stages and real flood comparison baselines.
- Added per-runtime-storage process ownership and persistent restart recovery, keeping tests/imports from touching a live instance's job status.

Verification is recorded in [runtime-hardening.json](validation/runtime-hardening.json). The protected replay matched 251 numeric maps across all seven cases. Known-value tests also check polygon references, transformed epoch meaning and shutdown when metadata writes fail. Browser checks confirmed saved runs, seven example cards, My Tools and the explicit flood-baseline explanation after restart; no console warnings or errors were captured. The README explains local profiles, recovery and the remaining deployment boundary.

The goal remains active while any required item lacks adequate current-state evidence. No public deployment or additional source-data deletion is authorized by this ledger itself.

Local hardening checks: **466 Python tests, 225 frontend tests, 251 exact protected-case maps**. The existing TestClient deprecation warning is retained in the receipt. Further production work remains as listed above.

## Storage safeguards and recovery · 0.8.2

- Added destination-filesystem safety reserves and write estimates for transfers, native extracts, geometry, caches and exports. Metadata readiness explains current disk space; estimates do not reserve OS capacity.
- Initial job metadata must persist before admission. A common worker guard records unexpected termination and releases the single-job admission state even if final metadata cannot be written.
- Added offline runtime backup, verification and fresh-profile restore with per-file SHA-256, member/size validation, no-overwrite gates and interruption markers. Protected example inputs need a separate backup.

Evidence: [storage-backup.json](validation/storage-backup.json), `tests/test_storage_budget.py`, `tests/test_workspace_backup.py`. This closes the local backup/restore mechanism gap; portable OS and separate-user delivery remain open. Docker work is deferred at the user’s request.

0.8.2 verification: **500 Python tests, 225 frontend tests, 251 exact protected-case maps**. The real offline snapshot contained 1,403 files; every included original file still matched its SHA-256 afterward. Its isolated restored server reopened all 15 saved results and one My Tool. [Restore rehearsal](validation/storage-backup-rehearsal.json). The private snapshot is in ignored `backups/`; protected examples remain outside its scope.

## Shared modular workflow contract · 0.8.3

- One declarative rule bundle now supplies elementary and scientific dependencies, units, output choices and minimum-file estimates to both backend and editor. Parameter schemas/defaults remain authoritative typed models.
- The editor previews actual insertion position and selected-output scope, rejects invalid ranges/calendar values, and handles an unavailable opening map after a method change. Missing/incompatible rule bundles disable execution.
- New result JSON and GeoTIFF tags retain the rule version/hash, with primary step I/O domains. Scientific compound blocks remain honestly labelled; a complete independent intermediate-raster inspection UI is still open.

Evidence: [workflow-contract.json](validation/workflow-contract.json), `tests/test_workflow_contract.py`, the frozen 0.8.2 acceptance fixture and seven protected replays. This is software contract/replay evidence, not new independent environmental validation.

0.8.3 checks: **517 Python tests, 233 interface tests, 3,528 matching typed metadata reports, 251 exact protected-data maps**. The frozen 0.8.2 acceptance oracle agrees on all generated cases (82 accepted, remaining cases rejected). Browser execution of the unchanged Mozambique workflow matched all 26 baseline maps, metrics and dated series; its GeoTIFF rule tags were checked. These limits and the remaining requirements remain explicit; the overall production goal is still open.


## Cancellation and renderer memory · 0.8.4

- Scoped cooperative cancellation now bypasses ordinary source/processing error handlers. API tests cover cancellation during a read, including a native wrapper error, and verify terminal status and a reusable worker. CPU stages, reference candidates, cached reads and atomic export publication have checkpoints.
- Incomplete cache/export temporaries are discarded; committed sources, caches and earlier result bundles are retained. An ongoing native library call may finish before cancellation takes effect.
- Colour interpolation uses bounded blocks while retaining exact pixels/ranges from a frozen 0.8.3 renderer. COG tile writes preserve numeric arrays across block edges. A separate-process 4-million-cell render measured about 76% lower peak RSS; this is not an end-to-end memory claim.

Evidence: [execution checks](validation/execution-export.json), [renderer memory measurement](validation/render-memory.json), `tests/test_execution.py`, `tests/test_streamed_exports.py`. **561 Python tests, 234 interface tests and 251 exact protected-case maps** passed. Scientific transfer validation, full internal-stage inspection, whole-pipeline resource limits, portable delivery and separate-user hosting remain open.


## Executed-step inspector · 0.8.5

New editable runs retain selected actual intermediate snapshots and link existing step outputs/diagnostics through numbered evidence cards. Users can inspect a step on the normal map and use the existing PNG/GeoTIFF exports. Shared editor/inspector labels hide irrelevant parameters; actual snapshot units, dates and coverage remain explicit. Older/guided results are not rewritten.

**575 Python tests and 243 interface tests** passed. Seven protected cases still reproduce **251 original maps**; their traces reference **32 declared steps and 17 additional snapshots**. A new browser Mozambique run matches all 26 original maps, metrics, dated series, opening PNG pixels and range. Its intermediate baseline opens on the map and exports with a stage-tagged GeoTIFF. [Evidence](validation/processing-trace.json).

This advances inspection of the executed workflow, but does not retain every internal temporary or intermediate date, expose arbitrary branches, or turn compound kernels into independently reorderable elementary operations. Those limits and the wider production requirements above remain open. No independent environmental accuracy or public multi-user readiness follows from these checks.


## Shared-range resource refinement · 0.8.6

The playback range resolver no longer retains and concatenates the finite values from every date. Bounded raster windows and exact float-key order statistics preserve the existing shared percentiles; large populations trade additional reads for lower working memory. Tests cover pathological values, mixed floating dtypes, cancellation and file preservation.

**591 Python tests and 243 interface tests passed.** All 17 saved-run display responses match the former algorithm exactly, with checked source/result hashes unchanged. The isolated 32-date range benchmark measured 87.3% less peak RSS. [Saved-run evidence](validation/saved-shared-ranges.json) · [Range memory evidence](validation/shared-range-memory.json).

This closes an identified all-date preview allocation issue. Whole-pipeline resource bounds, broader scientific/OS/usability evidence and separate-user hosting remain open. Docker work is deferred at the user's request; it is not part of the current implementation pass. No production-complete claim follows from this local improvement.


## Concurrent display work and browser cache · 0.8.7

One expensive preview/PNG function is admitted at a time. Excess requests receive an explicit short retry response; browser previews retry admission with a deadline and stop when superseded. Nested PNG resolver calls reuse the owning slot safely; exceptions/cancellation release it. The browser also bounds its estimated encoded preview cache by bytes and entry count, with LRU eviction and clearing when a result is reset. PNG lifecycle tests cover switching result panels during success/failure, preserving the original export identity and releasing the current button.

**596 Python tests and 254 interface tests passed.** A live 12-request burst admitted one render, returned eleven correctly marked busy responses, kept health available and recovered normal preview/PNG responses with unchanged hashes. Saved job records were unchanged. Browser checks confirmed latest-palette selection, shared-range two-frame playback and PNG completion, with no captured warnings/errors. [Evidence](validation/render-admission.json).

This closes the unbounded concurrent-render and retained-preview accumulation issues. It is not a whole-pipeline memory quota, independently validated environmental detector, separate-user queue or completed production release. The broader requirements above remain open.


## Regional comparison semantics · 0.8.8

Typed quantity/unit/component inputs distinguish measured-pair LOS displacement, a selected signed radar-component rate and constrained horizontal speed. Shared metadata/runtime rules reject incompatible units, ambiguous horizontal records, mismatched intervals, duplicates and unsupported evaluators before science processing. The named quantity uses its own regional series/common support. UTC matching, original unit conversions, matched/excluded counts, single-record spread limits and legacy assumptions are visible in reports. Settings show only product-relevant reference help; hidden reference JSON cannot block a GCOV run.

**626 Python tests and 260 interface tests passed.** All seven protected replays preserve the same 251 original numeric maps and prior metric/series receipts apart from app version. They ran with a separate temporary cache and zero remote science bytes. [Evidence](validation/regional-reference-contract.json).

This resolves a comparison-input ambiguity: earlier horizontal runs already used horizontal speed, while the generic input help described radar-component units without naming the quantity. New horizontal comparisons require explicit fields; legacy phase/radar-mode assumptions remain disclosed. No old saved result is rewritten. This is not new independent held-out validation or completion of the broader production scope.


## Study domains and auxiliary support · 0.8.9

Measurement masks/statistics now remain inside a supplied study domain while method-consumed references/stable samples can support corrections outside it. Empty study coverage cannot be accepted from auxiliary-only pixels. GOFF components share a study-only spatial-filter population. Elementary workflows retain/apply domain context and preserve phase reference samples until LOS conversion. Source diagnostics retain explicit wider scopes; result panels separate geometry counts from usable study coverage. COG tags/fingerprints record spatial-contract version 1.0; affected historical boundary paths receive a targeted rerun notice.

**642 Python tests and 265 interface tests passed.** Known-answer cases reproduce and fix water-area leakage, empty phase results/report failures and false glacier-component rejection. All seven protected cases retain 251 original numeric-map hashes, metrics and dated series. [Evidence](validation/spatial-support.json).

This closes the identified spatial-role/correction-population bugs. Broader independent transfer validation, complete resource/portable-delivery evidence and the other requirements in this ledger remain open.


## Reference-assistant resource admission · 0.8.10

The assistant previously bypassed the memory/disk gate used by normal analyses. One shared estimator now supplies both paths without changing prior estimates. Oversized assessments are rejected before a job is saved or a source is read, and worker/direct-kernel checks guard execution boundaries. Saved assessments retain resource evidence. Invalid memory configuration stops startup before storage ownership.

**653 Python tests and 265 interface tests passed.** Adversarial route tests reproduce the old bypass and check low disk, configuration failure, successful reference-free admission and a changed budget before worker reads. [Evidence](validation/resource-admission.json). This closes an admission-path inconsistency; it does not close the whole-pipeline memory-quota/stress requirement or establish new scientific accuracy. Docker remains deferred.


## Shared navigation and readability · 0.8.11

The interface now supports a first-Tab skip link, current-section/page-title semantics, logical heading focus, native keyboard tool selection, settings/tutorial destination focus and named dialogs. A delayed tutorial load cannot overwrite the workspace after explicit navigation away. Shared small-text styles were darkened on their checked backgrounds; scientific map palettes remain unchanged.

**653 Python tests and 274 interface tests passed.** Browser tasks covered seven tabs, all seven tools’ settings, tutorial Back, native Space/Tab selection, help/Escape focus return and the saved Wheeler result/catalog. All 1,743 snapshotted runtime/cache/protected-input files remain byte-identical. [Evidence](validation/keyboard-navigation.json). This advances the beginner-friendly interface requirement; it does not replace responsive-device, assistive-technology or novice-user evaluation and is not full WCAG certification. Docker remains out of scope.


## Native geometry allocation bounds · 0.8.12

The glacier geometry adapter no longer reads complete height cubes from originals for a small target area. Metadata/chunk/window bounds precede reads, exact spatial/height brackets retain the same interpolant, and bounded point batches expose cancellation. Native files remain unchanged and horizontal-only cache versioning preserves other caches.

**699 Python tests and 274 interface tests passed.** A frozen oracle and real Samudra Tapu comparison preserve all five geometry fields. Its protected replay and live browser run preserve 21 result maps, metrics, timeline and Rainbow overlay bytes. A synthetic fresh-process allocation comparison measured 71.95% lower peak RSS for this geometry path. All 1,743 earlier saved files remain byte-identical. [Evidence](validation/geometry-windowing.json).

This closes the unbounded full-cube geometry read. It does not bound the entire scientific stack, reserve OS RAM, supply independent glacier accuracy, or complete the broader production requirements above. Docker remains deferred.


## Local acceptance · 0.8.13

**706 Python and 274 frontend tests pass.** A fresh isolated Python environment installed the exact locked dependencies from public PyPI and passed the full API/restart gate: seven cases, 31 protected sources, 14 guided/editable runs, **502 exact original-map comparisons**, **655 preview checks**, seven saved/exported/reopened recipes and 14 runs reopened after restart. The measured peak child RSS was approximately 1.20 GiB for these cases; this is not a maximum-workload quota.

The live app was restarted at 0.8.13 with no active user job. All 21 saved jobs reopened with zero storage warnings. **1,899 runtime/example files remain byte-identical** across restart. Browser review shows all seven verified-input tutorials and no captured console errors or warnings. [Release integration](validation/release-integration.json) · [Local receipt](validation/local-release.json) · [Examples screen](screenshots/local-release-0.8.13.png).

New authenticated NASA transfers were not repeated: the live app is disconnected, and the acceptance run used the protected real inputs. Catalog/network availability and Earthdata authorization remain external dependencies; sign in for new downloads. The engineering gate does not turn case-study agreement into general environmental accuracy.


## Demonstration, explanations and comparison assessment · 0.8.14

The user-authorized priorities 1–3 are implemented: review all seven existing examples, select the strongest demonstration, standardize explanations across tools, and show what each comparison does and does not validate. Timber Fire is the numerical lead, with Mozambique and Mexico City supporting different measurements and explanation needs. Existing images, dates and processing settings are preserved. Fresh official-boundary evaluation distinguishes its radar-only support from the older radar/optical support, and shared-input author agreement from independent evidence.

Evidence: **723 Python / 278 frontend tests**, all seven guided/editable replays (**502 original maps / 655 previews**), all seven browser tutorials and real result guides. [Scientific comparison review](EXAMPLE_EVIDENCE_REVIEW.md) · [Browser checks](validation/example-evidence-browser.json). This completes these presentation/evidence-review priorities; no new held-out case, field validation or novice study is claimed.


## Transfer, usability and demonstration review · 0.8.15

Earlier validation working material (moved outside this project by its owner) recorded the approved Lucas Fire / Bang Pakong evaluations, unchanged protected replay, concrete usability fixes and recording-ready demonstration package. The fresh release gate passed 734 Python and 284 frontend tests, 502 original numeric-map comparisons and 655 previews. Optional tracking limits now produce explicit diagnostic unavailability without blocking P01/P02/P06 core maps. A completed edited introduction is available in About. No independent novice study, universal environmental accuracy, continuous live recording or new protected Example is claimed.
