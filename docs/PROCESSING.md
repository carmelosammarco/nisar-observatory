# Current processing methods

**Instrument scope:** all implemented tools use NASA/ASF NISAR **L-band (LSAR)** GCOV, GUNW or GOFF. Local originals and area subsets use the same scope. Frequency A/B are subbands; S-band and GSLC processing are not implemented. See [the mission source review](MISSION_SOURCE_REVIEW.md).

**Application 0.8.0 · reader 0.3.3 · scientific contracts 1.1.0**. Per-method algorithm versions are recorded in results; P03 combined processing is 0.8.0. The executable tool registry is `docs/tools.json`; the Tools page displays that registry. Original concept plans and older scientific audits are historical research documents, not current feature descriptions.

## Shared pipeline

1. Search the explicitly chosen BETA or provisional V1 collection through paginated CMR, up to 5,000 records per product. Fixed page sizes preserve offsets even for a custom limit such as 201. Truncation and skipped records remain visible. Release families are not merged. P04 alone offers explicit consent to join processing revision numbers within one release family.
2. Select one geometry/mode/polarization/release group per product and one version per acquisition or pair. Only products used by requested tools are read or checked for remote authentication. A run accepts at most 32 sources.
3. Read a bounded geocoded HDF5 window from a local original or authorized HTTPS byte ranges. Coordinates must be finite, regular and monotonic. Native windows exceeding 8 million pixels stop. Supported arrays must expose recognizable projection and coordinate metadata.
4. Remove native fill/nonfinite values and interpret product-specific quality **before averaging**. GCOV requires positive power and screens its source mask; GUNW screens coherence and component validity and retains one dominant component; GOFF requires SNR and explicit meter units. Unknown flag semantics stop rather than being guessed.
5. Export native accepted, missing and individual rejection fractions, together with coherence/SNR where applicable. Fractions are spatially aggregated native sample support, not environmental confidence. Rejection reasons are sequential/disjoint in normal screening.
6. Average valid contributors onto a separate EPSG:6933 grid per product. Default accepted-support cutoff is 0.5. Floors are 20 m GCOV, 80 m GUNW/GOFF, with at most 384 cells per axis (900 for GUNW runs including P04). Native spacing remains in source metadata. Grid posting cannot create finer source information.
7. Compare regional values on fixed common support. Empty common support is an error, never zero change. Supplied domains, affected areas, references and named zones are rasterized from validated WGS84 polygons. Added reference/stable polygons can retain needed comparison support outside the domain; offset summaries are then restricted to the study domain. Water playback uses common support; count/quality maps expose broader source evidence.
8. Save numeric COG GeoTIFFs, display PNGs, source/quality/correction manifests, settings, factual findings and generated candidate GeoJSON. Reader/cache and algorithm versions are explicit. Historical results and originals are not rewritten or deleted.

## GCOV baseline and water evidence

Valid **linear power** is averaged before `10 log10(power)`. The generic change layer is latest minus first dB. A separate baseline-departure layer uses the median of exactly the first N selected observations, or all observations through the supplied baseline-end date, leaving later comparisons. Insufficient count-based baselines are rejected rather than reduced. Standardized departure divides by `max(1.4826 × baseline MAD, noise floor)`, default floor 1 dB. It is a descriptive ratio, not a probability.

Water candidates use the supplied threshold (default −17 dB), or a threshold calibrated against independently sourced water/dry training polygons. The calibrated threshold maximizes training F1 over a bounded set of training-derived candidates; test labels do not choose it. Separate test polygons produce labeled-cell precision, recall, IoU, specificity and count bias. Duplicate labels are de-duplicated; conflicting class/train-test overlaps on the same date are rejected. These polygon cells are spatially correlated; no confidence interval or worldwide accuracy is inferred.

The three-state context map separates dry candidate (0), water candidate (1) and ambiguous band (2), default within ±1 dB of the threshold. Binary candidate areas remain explicit and separate from ambiguity. Precision/recall evaluate the binary threshold rule; ambiguity area is reported separately. Classification does not account for every radar-shadow, smooth-land or vegetated-inundation condition.

Five thresholds at the chosen value ±1/±2 dB expose classification sensitivity. Grid sensitivity averages already extracted valid linear power in 1×, 2× and 4× blocks, then thresholds it; common support may shrink at edges and its area is reported. This is not a re-extraction at every native resolution or a calibrated uncertainty distribution.

### Dated candidate objects

Four-neighbor connected components are retained by **physical area**, default 30,000 m². Dated objects link by overlap, with explicit parents/children for splits and merges. Candidate fractions are evaluated across acquired dates on each object's footprint. First observed active, last earlier fully inactive and first later fully inactive dates remain distinct. No uninterrupted activity between acquisitions is invented. Tracking is bounded to 1,000 objects per result; increase the physical mapping area or narrow dates/area when exceeded.

The GeoJSON contains WGS84 geometry, dates, physical area, links and footprint calendars. The result interface can display outlines, choose an object and return to its acquired frame. These are measured candidate objects, not guaranteed physical object identities.

### GCOV experience differences

| Tool | Implemented calculation |
|---|---|
| P01 Flood Memory | Two-date or longer comparison; optional date or largest consecutive new-water expansion; median pre-comparison baseline; new-water candidates; first later dry index and last-wet/first-dry day bounds. No later dry observation means unresolved. The event baseline and generic first-to-last map are separately labeled. |
| P02 Wetland Pulse | Acquisition-count occupancy, intermittent/always-water area, named-zone trajectories or clearly labeled geometric halves, counts, gaps and candidate histories. |
| P03 After Fire Observatory | Combined mode: separate HH/HV linear-power baselines per viewing group, absolute dB departures, latest available-view magnitude fusion, Gaussian smoothing, scene-relative robust score and physical-area patches. The geographic AOI intersects the supplied normalization domain before calculation. Legacy relative-reference mode remains separately labelled and uses reference-subtracted trajectories. |
| P06 Volcano Surface Diary | Latest smoothed departure, latest signed candidate patches, repeated same-sign evidence and first observed change. Original dates and the previous all-later-dates method remain available. These are not validated lava maps. |

GCOV main-channel selection now exposes HH, HV, VV, VH and supported compact channels. Auto keeps its original co-polarization preference. With HH/HV or VV/VH comparison enabled, the ratio is always cross/co even when the main channel is HV or VH; matched-pair provenance and a versioned cache adapter prevent an HV/HV zero contrast. Wetland Pulse joint sigma-zero still requires Auto/HH.


Optional matching cross/co-polarized power contrast uses delivered diagonal terms only. Missing companion channels are reported. It is not a full polarimetric decomposition or a land-cover classifier.

## GUNW phase evidence

Recognized phase units are radians. Retain coherent pixels in one native component before aggregation; component IDs are file-local. Reference cells must be identical and finite across selected pairs, with comparison cells outside the reference. Polygon references take priority over the rectangle when supplied. The app retains counts and spatial reference spread; multiple polygons show origin-shift sensitivity.

Referenced phase-equivalent change is `−λ(phase − reference median)/(4π)` in mm. Wavelength comes from source metadata, never a guessed constant. Exact elapsed days produce interval-average mm/day. Spatial reference spread is not a confidence interval, and an interval rate is not vertical motion or a fitted subsidence velocity.

### P05 event-interval displacement and coverage mosaics · 0.4.3

The primary P05 map is referenced relative LOS displacement in **cm**, calculated as `−λ(phase − median reference phase)/(4π) × 100` with wavelength from delivered metadata. It retains original mm pair maps and mm/day interval rates. Event bracketing uses reference-pass end and secondary-pass start from all four original filename timestamps when available; the event must lie strictly between them. Date-only input excludes boundary days. The shortest eligible pair is selected within each group.

An explicit `quake_mosaic` option is allowed only for a P05-only run. Adjacent track/frame groups must retain the same ascending/descending direction, bandwidth, polarization configuration and processing release. Each group runs the single-group phase workflow separately. At least 25 identical valid reference cells across all selected observations are preferred inside the declared reference; otherwise independent reference supports are explicitly reported. no global common-footprint intersection is imposed across spatially adjacent groups. Missing event bracketing or reference support in any group stops processing. Source read failures also stop P05 rather than silently reducing selected coverage.

At overlapping cells the mosaic chooses the valid source with highest delivered accepted-sample coherence; absent coherence ranks below finite coherence, and ties follow sorted group order. This is a presentation choice, not an optimal geophysical inversion. The result exports the source-index key, valid group count, max-minus-min overlap difference and all per-group maps, original intervals, native quality evidence, reference counts, corrections and exact dates. Opposite viewing directions and revisions are not joined. Geometry, post-event timing and reference offsets can all cause overlap differences; these are not calibrated error estimates. No east/up decomposition, overlap averaging, interpolation, background subtraction or earthquake-only causal attribution is performed.

All tools use shared Default, Diverging and Rainbow display controls. Rainbow uses one 256-stop lookup across products; Diverging has a light midpoint. Use Custom to set comparison limits such as ±50 cm (or ±500 mm for original displacement layers). A symmetric Diverging scale has white at zero; a symmetric Rainbow scale has green at zero. Other quantities retain automatic ranges in their own units. Numeric exports never change with palette/range. Historical P05 results remain available with their original outputs.

### Correction manifest

An explicit option subtracts the matching delivered `ionospherePhaseScreen` **before aggregation**, requiring declared radian units and matched native coordinates. Missing/unsupported requested screens stop the extraction. The correction array and operation are retained. Source GUNW screens are not applied by default according to the official guide.

Tropospheric and solid-Earth-tide lookup-table correction is **not automated**. A 3D correction lookup requires verified height interpolation, geometry, sign and prior-application handling; it is not safe to subtract it as an arbitrary 2D raster. The app does not claim that ionospheric subtraction alone makes a geodetically corrected displacement product.

### Graph and network checks

Acquisition epochs are normalized to exact UTC instants. Pair incidence rank, connected components, redundant edges and exact-endpoint triangle closure are recorded. A closure check is an internal consistency test, not accuracy validation.

For P05, the automatic network fit requires a connected full-rank graph and at least one redundant pair cycle. Ordinary least squares solves pair changes with the first epoch fixed to zero. Outputs include the reconstructed phase-equivalent epoch series, pair residual RMS and a fitted linear phase-equivalent trend. No MintPy installation, atmospheric correction workflow or geographic/vertical decomposition is implied. A nearest-neighbor-only chain has no redundant cycle and remains interval evidence under that gate. P04 uses the separate, explicitly limited rate workflow below.

### P04 connected-pair motion rates

P04 automatically attempts a rate when at least two connected pairs link three distinct acquired UTC epochs. Four or more dates over several weeks are preferable. A connected full-rank graph is required, but redundant cycles are not mandatory: the interface explicitly states when independent closure cannot be checked. Disconnected records or a single pair retain interval maps and a reason; no unsupported trend is invented.

The same spatial reference cells must survive every selected pair. Each pair subtracts its reference median; phase conversion uses its metadata wavelength. Let `d` be these relative pair changes in mm and `B` the chronological pair incidence matrix (−1 at start, +1 at end). Solve `B[:,1:] × x[1:] ≈ d` by ordinary least squares, fixing `x[0]=0`. This handles overlapping intervals without double counting. It is an unweighted exploratory reconstruction; pair errors can be correlated.

At each common pixel, fit `x(t)/10 = a + v × elapsed_days/365.25` across acquired epochs. Export `v` in cm/year, `v/12` in cm per mean month, and the reconstructed acquired-date cube in cm. The first-to-last change is the final reconstructed epoch, not necessarily the fitted trend times duration. The regional chart is the spatial median of the same dated maps; the median fitted rate and slope of regional medians need not be identical.

Two zeros have distinct roles: reference ground sets spatial zero; the first acquisition sets temporal zero. Neither proves the ground is stationary in an absolute frame. Positive LOS means toward the satellite, negative away. Without another viewing geometry and assumptions this is not vertical subsidence.

Trend-fit RMS describes departures from a straight line, in cm. Pair residual RMS describes mismatch of the incidence model, also in cm. A tree fits all pair constraints exactly and therefore has zero pair residual by construction; it cannot independently check phase unwrapping. Neither residual is ground-truth accuracy or an uncertainty interval. No interpolation creates additional observed dates.

Native ionospheric subtraction is recommended by the P04 guided setup and recorded explicitly; missing required screens stop the read. Tropospheric/tidal corrections, DEM-error estimation and vertical decomposition are not implemented. A direct API request retains explicit options rather than assuming correction.

By default processing revisions remain separate. P04 alone can explicitly join revision numbers in the same release family and geometry; original group names and an algorithm-change warning remain in the result. BETA X revisions are never silently joined with provisional P revisions. Independent regional reference evaluation, if supplied, continues to compare original pair medians in mm, never a cm/year rate against a pair displacement.

The [Mexico City comparison](../Examples/P04_Mexico_City/references/MEXICO_ORIGINAL_REPLAY.md) uses six downloaded originals and compares against the NASA illustration as a qualitative benchmark. NASA’s image legend uses cm/year; its article also discusses cm/month. Similar patterns are not numerical validation against NASA’s unavailable velocity raster.

P13 additionally fits `intercept + linear term + annual sine + annual cosine` only when at least six reconstructed epochs span a full year and the design is full rank/well conditioned. The annual amplitude and residual describe this phase model; they are not thaw depth or a validated permafrost process. Unmet conditions produce a reason, while pair maps and rate spread remain usable.

P05 accepts an explicit timezone-aware event timestamp, checking after the reference acquisition window and before the secondary start when filename windows are available. Date-only input retains strict calendar-day bracketing. The shortest matching pair is selected; other non-bracketing intervals are listed as timing controls, not automatically stable terrain.


## GOFF movement evidence

Native SNR-screened offsets with explicit meter units are divided by exact elapsed pair days. Raw screened rates remain available. An optional spatial filter rejects deviations from the scene median above `max(8 × 1.4826 × MAD, 1 meter)` by default. Optional local 3×3 consistency is a separate setting. Both can remove real localized motion; rejected-cell maps and a filter-off comparison support inspection.

A supplied stable-terrain polygon permits optional median rate-bias removal. The source, stable-cell count, estimated bias and application flag are retained. Delivered companion components and pre-spatial-filter two-component magnitude remain explicitly in radar geometry, not geographic horizontal speed. No acceleration claim is inferred from differences between interval averages.

## Verification and use

Synthetic known-answer tests check formulas, mask ordering, native contributions/cache, split/merge histories, physical mapping area, chart/map statistic agreement, exact timing, network reconstruction and injected annual signals. Retained real GCOV/GUNW/GOFF originals exercise all seven tools and georeferenced exports. Synthetic event fixtures in engineering tests are explicitly identified and are not environmental findings.

The independent evaluation functions are implemented; independently sourced labels/measurements are still required for an actual accuracy assessment. Supplying a citation field cannot programmatically establish that a source is independent or representative. See [current verification](VALIDATION.md) and [input formats](INPUTS.md).

Method background: [GCOV](https://nisar-docs.asf.alaska.edu/gcov/), [GUNW](https://nisar-docs.asf.alaska.edu/gunw/), [GOFF](https://nisar-docs.asf.alaska.edu/goff/), [ASF change-detection notebook](https://github.com/ASFOpenSARlab/NISAR_Cookbook/blob/main/notebooks/NISAR_GCOV_SARChangeDetectionMethods.ipynb), [MintPy methods background](https://doi.org/10.1016/j.cageo.2019.104331). Published performance is not transferred to this implementation.


## Reference suitability and appearance · application 0.4.1

The P04 LOS numerical algorithm remains 0.4.0 and native reader/cache remains 0.3.0. Reference assistant 1.0 (`backend/reference.py`) is a separate preflight assessment, never a stable-terrain classifier. It evaluates bounded windows within the selected domain, excluding supplied affected polygons, and requires 25 common cells plus 80% coverage. Rank is worst-pair median accepted-sample coherence, shared fraction, then maximum per-pair spatial phase MAD. Coherence below 0.70 is flagged for review, not interpreted as a universal accuracy threshold. Up to three separated patches are retained; the exact screen and measurements are saved.

Reference-choice rates use each candidate’s per-pair phase median relative to Candidate 1, source wavelength conversion and the same connected-epoch trend model. These scalar differences describe the shift of spatial zero, not absolute stability. The current reference is assessed separately when supplied, including an empty-support warning. Candidate 1’s zero is imposed by the comparison. A coherent uniformly moving patch can rank highly and is explicitly not called stable. No elevation or land-cover classification or external stable-ground evidence is inferred.

Each saved assessment has a fingerprint over source identities, study bounds, screening/correction/channel/grid settings and domain/affected polygons. Candidate adoption requires an exact matching context and bounds. Reference polygons must be explicitly replaced before a candidate rectangle can be used. The prevalidated selected-candidate record is copied into the analysis job/result, preserving its evidence if the separate assessment is later deleted.

Display palettes and ranges are independent of all science calculations. Arbitrary-length color lookups are interpolated with missing pixels transparent. The Rainbow lookup reproduces the Jet colors used by the figure; the rate preset is ±30 cm/year or ±2.5 cm/month. Categorical and quality maps retain their established colors. Shared playback ranges pool acquired-date frames with matching units/kind; other rate/change summaries are not mixed into those limits. Custom ranges reset on unit changes. The interface reports clipping, fallback and constant-frame behavior.


### Native valid-sample masks · reader 0.3.1

GUNW valid-sample masks are decoded from their documented source attributes before averaging. Packed uint32 words are read through float64 to preserve every bit; the low byte’s reference and secondary decimal subswath digits must both be nonzero. Fill/invalid words and anomaly bits 8–23 are excluded. Water status alone is not a displacement rejection. Bit 24 preserves interpolated-ionosphere provenance. Legitimate zero phase is retained when masks permit it. Native rejection fractions are exported. An unknown delivered mask schema fails explicitly; absent masks carry a warning. Cache version 0.3.1 bypasses old arrays without deleting them. See [the P05 investigation](../Examples/P05_Venezuela/references/p05_OVERLAP_REVIEW.md).

## Shared reference assistant · application 0.4.4

Assistant 2.0 supports P03, P04, P05 through one API and interface. It shares the processor grid calculation and quality reader. Coverage-seeded windows at up to three sizes preserve the 25-cell/80% screen while finding narrow overlaps. GCOV comparison uses per-cell median-baseline departures followed by reference median subtraction, matching P03; phase comparison uses the source wavelengths and per-pair reference medians. Only P04 fits reference-rate sensitivity. P05 shows cm offsets. P05 accepts explicit compatible adjacent-group coverage and checks event bracketing. Its comparison-ground check uses union coverage, while reference candidates still require common cells across every source.

Fingerprints include the chosen tool, assistant/reader versions, source identities, grid/quality/correction/channel settings, event/mosaic and baseline choices, and domain/affected geometry. Cross-tool or stale adoption is rejected. Every supported tool saves the chosen assessment evidence in its result. No stable or unaffected reference is inferred automatically. See [the shared guide and real-data findings](REFERENCE_ASSISTANT.md).

## Shared processing review · application 0.4.6

All selected-source read failures now block every tool using the failed product, preventing silent changes to the temporal record. Independent product workflows remain separate. P07 metrics retain full-grid valid-fraction denominators; P03 reference diagnostics follow the declared median baseline. First-to-last GCOV changes are labeled explicitly. Reference assistant 2.1 samples the full region and prefers larger support within quality screens. Frontend defaults/restoration are centralized and settings are serialized only for requested products/tools; setup preserves explicit choices. All phase tools share the explicit recommended-settings action. See [the current tool catalogue](TOOL_CATALOGUE.md) and [Mexico City example](../Examples/P04_Mexico_City/README.md).


## P02 Wheeler Marsh comparison

The prepared Wheeler Marsh rectangle is an extraction window around a published tidal-marsh study site, not the published boundary itself. Optional NWI estuarine emergent polygons define a 2.86 km² inventory domain and named regularly/irregularly flooded zones. They are independent of the radar classification, but not date-specific water labels. Their original imagery vintage was not established here.

P02 algorithm 0.5.0 adds **HH/HV · sigma-zero (paper-inspired)**. Native linear HH and HV power are multiplied by the delivered gamma-to-sigma factor before quality-screened averaging. Both channels use the same valid native support; a cell is a candidate only when **HH < −14 dB AND HV < −23 dB** (editable). Missing required inputs stop this method explicitly; there is no silent single-channel fallback. The previous single-channel gamma-zero calculation remains selectable and older saved setups retain it.

The common domain is finite in both channels on every selected date. Frequency, date maps, patch tracking and zone statistics use this support. The ambiguity layer respects the joint AND rule; threshold sensitivity shifts both thresholds together by ±1/±2 dB and is not a full two-dimensional parameter search. Grid sensitivity averages converted linear powers before reclassification. Optional independent held-out labels evaluate the fixed rule without fitting it. Exported latest HH/HV sigma-zero and joint accepted-support layers make the radiometry inspectable. No Enhanced Lee filter, calibrated tidal-lag model, depth or volume is implemented. Tide association is not classification accuracy. See [the integrated-method comparison](../Examples/P02_Wheeler_Marsh/references/P02_HH_HV_COMPARISON.md) and [the original study record](../Examples/P02_Wheeler_Marsh/references/P02_WHEELER_MARSH.md).


## P03 combined HH/HV change · version 0.8.0

New P03 setups default to combined change: at least three pre-fire baseline dates and one post-baseline date **per viewing group**, both HH and HV. No unaffected reference rectangle is used. Each view uses its own median linear-power baseline; absolute HH and HV dB changes are summed, latest valid views averaged, normalized-Gaussian smoothed (80 m sigma), and robustly standardized across the selected land window. Default candidates use z ≥ 2 and four-connected patches ≥ 10 ha. Native support and missing channels are checked explicitly. Local UTM grids are bounded to 2048 cells per side and four million cells.

The previous reference-relative P03 method remains selectable and continues using the shared reference assistant. Earlier P03 sections describe that method. Combined outputs include a dimensionless change score, candidate mask, view count, individual-view dated magnitudes and signed channel diagnostics. A change candidate is not a burn-severity or recovery measurement. Water, terrain and window selection require review; no DEM/LOS shadow mask is applied. See [the exact protected Timber tutorial](../Examples/P03_Timber_Fire/README.md) for tested dates, settings, real-data agreement and limitations.

## P06 evolving surface change · 0.7.1

The opt-in `surface_method=evolving` uses one compatible GCOV group and the existing per-cell median dB baseline. Every quantitative comparison uses common valid support. The rotated UTM envelope is clipped by cell centres to the selected WGS84 rectangle before P06 evolving processing, so surrounding envelope corners do not contribute area. For each later date, Gaussian smoothing of the signed dB departure divides filtered values by filtered finite support and retains missing cells. The shared `smoothing_m` is sigma, not FWHM; effective width is about 2.35 sigma. Positive and negative threshold masks are separately filtered using four-neighbour connectivity and physical minimum patch area. Default new setup: 20 m cell spacing, 40 m sigma, ±3 dB and 30,000 m².

`surface` is the latest retained signed-change footprint. `confirmed_change` means same-sign change on at least two consecutive post-baseline observations ending at the latest date; it does not establish continuous persistence. `repeat_count` counts that trailing run. `first_change` records the first sampled qualifying date; its JSON and PNG date keys use `first_change_calendar`. With one later date, repetition is unavailable and omitted from Main results, while the supporting raster remains downloadable. Baseline chart values are zero by definition.

The bounded local UTM grid reuses P03’s metric grid and missing-data-preserving filter helpers without changing P03 calculations. At most 2048 cells per side and four million cells; larger requests return a clear size error instead of silently coarsening. This method is restricted to a P06-only request. Historical recipes without a method retain `legacy`, whose original unsmoothed all-later-dates rule remains available. The GUI offers evolving change for new setups.

Brightness candidates are not temperature, volume, eruption probability or validated lava boundaries. Snow, wetness and terrain can contribute. A during-eruption baseline measures only subsequent change. NASA’s Krasheninnikov animation is a qualitative dated reference with oblique rendering, not georeferenced ground truth. See the [five-date evaluation](validation/krasheninnikov/README.md).

## P07 constrained horizontal motion (algorithm 0.4.2)

Radar mode remains available without geometry. Horizontal mode first requires both components to be finite on the same native samples, after source fill/SNR screening and before grid averaging. It reads the delivered LOS/along-track ENU vector cubes and incidence angle, interpolating over native height/y/x axes at an explicit constant ellipsoidal height with no extrapolation. Vector descriptions and units are checked; horizontal unit-vector and incidence consistency are tested. At each cell it solves a 2×2 system with vertical velocity fixed at zero. Singular, invalid or poorly conditioned systems are excluded rather than regularized silently. Signed east/north rates, speed, bearing, conditioning and a configurable vertical-motion sensitivity scenario are exported. That scenario is a vector-bias magnitude, not an accuracy estimate. No terrain-slope constraint, full 3D solution or automatic registration correction is claimed.

The main statistics, dated speed maps, temporal spread and common-support chart refer to horizontal speed in this mode. Signed radar components and radar-plane norms remain explicitly labelled diagnostics. All measurements are interval averages; m/year annualizes by 365.25. One acquisition group is used per run. See the [real Samudra Tapu geometry investigation](validation/samudra-tapu/geometry/README.md).



## Refinement contracts · 0.8.0

All Gaussian smoothing paths use the same reflected-boundary normalized convolution, requiring at least 30% finite kernel support and retaining missing central cells. Sigma is in metres divided by actual grid spacing. Repeated map transforms keep their own parameters rather than replacing internal method settings. Removing optional water tracking stops the connected-object computation.

Fast metadata readiness is shared by guided and editable run routes. It checks dates, viewing groups, baseline availability, reference declaration, pair connectivity/event bracketing and an estimated grid-memory budget. It never substitutes for native channel, quality, common-pixel or viewing-geometry checks. New exports retain readiness, a result interpretation passport, explicit class semantics and a scientific execution fingerprint separate from display settings.

Cache identity includes the complete CRS/affine grid and source generation, not just dimensions and cell spacing. GeoTIFFs include measurement descriptions, units, available classes and reference/record provenance. [Current verification and scientific limits](VALIDATION.md).


## Explicit regional measurement comparisons · 0.8.8

GUNW checks original measured-pair regional LOS medians in mm, with compatible displacement-unit conversion; it does not compare a fitted annualized rate with a pair displacement. GOFF references explicitly choose either the selected signed radar-component rate or the constrained horizontal-speed median. In horizontal runs the component series remains separately retained and can be checked without confusing it with speed. Quantity, component, canonical units, original values, actual matched intervals and common support are recorded.

Metadata readiness rejects mismatched/ambiguous reference specifications before science reads. Matching uses UTC calendar dates and requires exactly one selected interval. Duplicated interval/value/source records cannot inflate the sample count. Missing/nonfinite regional summaries are excluded explicitly, with matched/requested/excluded counts. Unit conversion is dimension-preserving and uses the declared 365.25-day year; no geometry or displacement/rate conversion is inferred. The regional statistic is a median, so point measurements and spatial means require a separate representativeness justification. Citations supplied by a user are not independently authenticated.

Legacy phase and radar-mode reference records retain their earlier assumed quantity/unit with a visible warning. Old horizontal-mode help only described radar components even though its primary series/evaluation used horizontal speed; new horizontal checks require an explicit quantity and unit to resolve that ambiguity. Existing saved runs remain unchanged. This feature provides a transparent comparison mechanism, not new independent scientific validation of the seven cases.


## Spatial roles and custom study boundaries · 0.8.9

Study boundaries limit scientific measurements and regional statistics. Reference/stable-ground samples outside them may support a normalization or bias diagnostic, while raw/source-quality/intermediate maps remain separately identified diagnostic evidence. GUNW requires actual common comparison support inside the study outside its reference. A domain with no data cannot produce a successful blank phase result or fail later while formatting an empty median.

Both glacier components use the same study population for their spatial filters. Extreme second-component values outside a study must not reject valid inside motion. Native-quality-screened stable samples outside the domain are reserved for their separate median bias check; they do not set the moving-domain cutoff. Known-vector tests recover 5 m/day with and without an added stable-ground bias.

The same domain rule now applies to elementary ordered workflows, which previously retained reference geometry but did not apply a supplied domain. Other context roles remain annotations unless a relevant scientific block consumes them. Result panels explain geometry counts versus actual usable study coverage; COG tags and the execution fingerprint record the spatial contract. Existing saved files are never rewritten.


## Native GOFF viewing-geometry windows

Horizontal processing keeps the existing ENU-vector convention, constrained zero-vertical inversion, height assumption, conditioning and rate units. The geometry reader now selects the same interpolation vertices from the source before loading cube data: two height planes and the spatial bracket of actual transformed analysis-cell centres. It preserves descending/nonuniform axes, exact-grid boundaries and missing-neighbour behaviour; no outside-coverage extrapolation is introduced.

A source-axis metadata bound and HDF5 chunk check precede cube reads. Retained float64 geometry is limited to 64 MiB and target interpolation to batches of 65,536 points; output maps and native-library workspaces are additional. Geometry metadata reports source/read shapes, selected indices, height and resource scope. Adapter `goff-geometry-2` receives its own horizontal-cache identity; older cache files, originals, protected subsets and saved results are preserved. Native subset files keep their delivered height range on disk; the two-plane selection applies to a processing read, not destructive editing of the subset.

The [protected Samudra Tapu replay](validation/workflows/seven-examples/P07_Samudra_Tapu.json) records the numerical checks for the bundled case.
