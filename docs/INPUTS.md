# Inputs for the implemented tools

Normal exploration starts with an area, compatible NISAR observations and a tool. The additional controls below support focused studies and independent evaluation; they are optional unless that tool explicitly requires them.

## Archive release for live search

New explorations start with **Validated**. This release initially covers NISAR L-band Level 2 acquisitions from 21 October 2026 onward. Choose **Provisional** or **Beta** in Area & analysis settings for older dates. Each search covers one release. The saved examples keep their exact source files.

Use observations from the same archive release when possible. Processing differences can resemble surface change. The readiness check flags selections that mix known releases. Files imported without archive metadata may show an unknown release. [ASF archive availability](https://nisar-docs.asf.alaska.edu/availability-overview/).

## Radar band and supported files

Every tool uses **L-band** GCOV, GUNW or GOFF, discovered from NASA/ASF or imported locally. Readers require the `LSAR` science group. GCOV/GUNW/GOFF are Level 2. S-band (`SSAR`), GSLC and other mission products are not supported here. Frequency A/B are product subbands, not the L/S instrument distinction. Earthdata Login is a general NASA account; the configured product collections and readers determine this app’s L-band scope. See [the reviewed mission background](MISSION_SOURCE_REVIEW.md).

## Spatial context

In **Area & analysis settings**, draw a named rectangle or import WGS84 GeoJSON. The zone-only example download cannot silently become water-validation truth. A FeatureCollection supports at most 100 Polygon/MultiPolygon features and 10,000 vertices, with finite coordinates between 85°S and 85°N. Invalid geometry stops with an explanation.

| Property role | Effect |
|---|---|
| `domain` | Restricts the study footprint. Multiple polygons are combined. |
| `affected` | Selects P03's comparison area independently of the reference. |
| `zone` | Named comparison zones for P02. |
| `reference` | Reference polygons for phase and reference-normalized scattering; supplied polygons take priority over the blue rectangle. |
| `stable` | Defines independently justified stationary terrain for optional GOFF median-bias removal. |
| `water`, `dry` | Independent water-class labels, requiring `date`, `split` and `source`. |

Example of a **user-defined comparison zone**, not a validated water label:

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {"name": "North comparison zone", "role": "zone", "source": "user-defined zone"},
    "geometry": {"type": "Polygon", "coordinates": [[[4.53,43.48],[4.55,43.48],[4.55,43.50],[4.53,43.50],[4.53,43.48]]]}
  }]
}
```

For independently sourced water/dry polygons, properties must include `role: "water"` or `"dry"`, `date: "YYYY-MM-DD"`, `split: "train"` or `"test"`, and a nonempty independent source citation. Labels must match a selected acquisition date. Provide both water and dry training classes when calibrating a threshold. Test labels are not used to choose the threshold. Conflicting class or train/test overlaps on the same date are rejected; duplicate labels are de-duplicated. Use spatial/date separation and representative labels when designing the evaluation. Nearby cells are not independent field samples.

A citation string is provenance, not proof of independence. Do not use the app's own water candidates as independent test truth.

## Study boundary and auxiliary samples

A `domain` polygon restricts **measurement maps, summaries, filter populations and area counts**. It does not enlarge to include a reference or stable-ground polygon. If no common usable data remain inside the study, processing asks for revised inputs rather than accepting auxiliary-only coverage as a result.

GUNW and reference-based GCOV may retain a separate reference outside the study to establish their relative zero. GOFF can retain outside stable-ground samples for a median-bias diagnostic/correction. These auxiliary samples retain native-quality screening; outside stable ground does not set the moving study's local/global spatial-filter population. Both GOFF components follow that same rule.

Source-quality, raw-source, reference-support and intermediate maps may show wider diagnostic support; they are labelled separately and do not enlarge regional measurement statistics. Their GeoTIFFs include `spatial_scope`; a supplied-domain run also records spatial-contract version 1.0. Geometry-mask cell counts and actual valid study support are explained separately in results.

Elementary editable workflows now retain the shared spatial context. They apply `domain` geometry, and a GUNW LOS step also uses `reference` geometry. Other roles remain annotations until an appropriate scientific block uses them; an annotation alone does not add a classifier or independent validation. Supplied polygons remain limited to the analysis grid. The existing grid/bounding-box rules and cell-centre rasterization are unchanged.

Affected older domain results are preserved with a targeted rerun notice. The existing already-clipped combined fire, evolving-volcano, domain-only wetland and unfiltered glacier examples are not blanket-labelled broken. Default/example numeric results remain reproducible; a custom run affected by the earlier boundary bugs must be rerun to apply the fix.

## Regional reference observations

This optional check compares **supplied regional measurements**, not automatically verified truth. Enter a JSON array in **Area & analysis settings → Advanced → Compare supplied regional measurements**, or import its JSON file. The browser assigns the selected product if `product` is omitted; explicit product labels are recommended. Only matching-product records are used. Maximum: 500 records, with imports smaller than 2 MiB.

Each new record needs `date`, `end` (UTC acquisition calendar dates), `value`, `source`, `quantity` and `unit`. Use **one physical quantity per check**, matching exactly one selected pair per record.

| Reference quantity | Product / solution | Accepted meaning and units |
|---|---|---|
| `los_displacement` | GUNW, single-group P04/P05 | Signed relative LOS displacement across a measured pair, positive toward the satellite. `mm`, `cm`, `m`, converted to mm. P04 checks the original pair median, not its annualized trend or a vertical measurement. |
| `radar_component_rate` | GOFF, radar or horizontal solution | Signed interval-average rate. Also provide `component: "slantRangeOffset"` or `"alongTrackOffset"`, matching the selected component. |
| `horizontal_speed` | GOFF horizontal solution | Nonnegative horizontal-speed estimate under the zero-vertical-velocity constraint. Uses the horizontal series and its common usable footprint, not the signed range or along-track series. |

Rate units are `mm/day`, `cm/day`, `m/day`, `mm/year`, `cm/year` or `m/year`. They are converted to the run's selected m/day or m/year, using 365.25 days per year. Original values/units are retained. **A displacement is never converted into a rate or vice versa automatically.**

Format example only — the following value is illustrative, **not an independently measured Samudra Tapu reference**:

```json
[
  {
    "product": "GOFF",
    "quantity": "horizontal_speed",
    "unit": "m/year",
    "date": "2026-01-01",
    "end": "2026-01-13",
    "value": 100,
    "source": "FORMAT ONLY — replace with a documented matched regional median"
  }
]
```

For a radar-component comparison, use `quantity: "radar_component_rate"` and explicitly name the matching component. Do not use a published glacier speed as a signed range rate, or vertical GNSS displacement as a LOS measurement. Match the **regional median**, valid spatial footprint, exact interval, viewing geometry and reference origin. A point sensor or regional mean is not automatically representative of this median.

New reports show the physical quantity, component, applied units, common support, app-minus-reference bias, error metrics and matched measurements. Bias-removed RMSE is unavailable with only one compared record, because zero would follow by construction rather than measure variability. Unavailable matched summaries are listed as exclusions; they are not zero error. Duplicate interval/value/source records are rejected. The result JSON keeps the full comparison and unit-conversion record; the browser previews up to 20 matched rows.

Older phase/radar-mode records without both quantity and unit retain their earlier interpretation with an explicit assumptions warning. A legacy record with no end must identify exactly one selected pair. **Horizontal-mode runs reject unspecified quantities/units**, because the older help described radar-component references while the horizontal mode compared its horizontal-speed series. No existing saved result is rewritten. P05 mosaics require separate per-group reference checks because their dates, geometry and footprints can differ. Elementary transformed workflows do not silently claim a regional reference evaluation.

## Event timing

P05 accepts an exact event time with timezone, such as `2026-08-01T12:30:00Z`. Use independently documented timing. The calendar-date field is a fallback with strict before/after day bounds. When acquisition windows are known, an event during the reference acquisition is not accepted as a clean pre/post comparison.


## Baseline and model controls

- GCOV baseline count defaults to 1; the optional end date overrides it. Leave at least one later observation. Flood Memory has a separately identified pre-comparison median baseline.
- Minimum patch area defaults to 30,000 m² and stays in physical units as grid spacing changes.
- Ambiguous-water half-width defaults to 1 dB; it is a sensitivity band, not a statistical confidence bound.
- Cross-polarization comparisons are optional extra reads, not external independent evidence.
- Requested ionospheric subtraction requires a matching delivered screen explicitly in radians; missing or unsupported requested correction data stops extraction.
- P04 rate fitting needs connected common support and at least three dates; a chain is explicitly labeled as having no independent closure check. Other phase tools require a redundant cycle for their network fit. The result explains unmet conditions; acquired pair views remain usable.
- GOFF local screening and stable-terrain bias removal are explicit optional choices. They can change real motion; inspect raw/rejected maps and rerun without filters.

Every saved run retains the options and data sources actually used. Changing an input requires a new run; historical numeric results are preserved.


## P04 motion-rate walkthrough

Use the same steps in other areas, with dates, geometry and a reference appropriate to that location.

| Step | Input and purpose |
|---|---|
| Area | Draw a study region; Mexico City verification bounds are west −99.40, south 19.14, east −98.75, north 19.65. |
| Sources | Select P04, then Use saved originals. For a live early-mission search select BETA and dates October 25, 2025 through January 17, 2026. These are six measured pairs linking seven acquisitions. |
| Compatibility | Track 113, descending, frame 079, frequency A, HH. The first pair is X05009; the later pairs are X05010. P04 setup requires explicit consent to join these processing revisions. This can introduce artifacts; it is not general permission to mix viewing geometries or release families. Select all six once the joined group is displayed. |
| Reference | For the verification only: west −99.28, south 19.40, east −99.24, north 19.44. Draw/reference-coordinate entry uses WGS84. This is an assumed reference, not an independently established stable station. Inspect its common support and compare other defensible references. |
| Settings | 80 m requested posting, coherence ≥0.30, native accepted fraction ≥0.50, subtract delivered ionospheric screen. Area limits can coarsen the actual grid; the saved grid gives the real posting. |
| Results | Opening rate in cm/year; same rate divided by 12 in cm/month. Seven acquired-date reconstructed maps and chart in cm, six original pair maps in mm, fit residual, pair residual and quality/reference maps. |
| Reopen | Results are retained in Your runs. New exploration clears working selections without deleting saved originals or completed runs. |

A minimum of **two connected pairs / three dates** supports the P04 rate calculation. More dates do not guarantee good data. Every compared pixel and each reference cell must survive all selected pairs; a large series can therefore have less common coverage. Single or disconnected records keep pair-only results and an explanation. No external dataset is required to execute P04; independent data are still needed to validate geophysical interpretation.

The spatial reference establishes relative motion, while the first date establishes zero accumulated change. Choose a reference outside the suspected moving zone with defensible stability, on the same coherent component/support. Positive is toward the satellite, negative away. The displayed rate is LOS, not automatically vertical sinking. The app does not infer safe buildings or structural damage.


## P04 reference area assistant

1. Select an area and the GUNW pairs you intend to process. Choose P04 and **Review inputs & reference** (or **Set up inputs**).
2. Press **Find or check a reference**. The assistant reads those same quality-screened pairs on the P04 grid. Saved originals are reused without an Earthdata login; remote reads need your own session. No analysis reference is needed to generate candidates.
3. Inspect the candidate cards and **Locate on map**. Shared coverage is the proportion of patch cells usable on every pair. Worst-pair coherence is the lowest pair’s median of aggregated accepted-sample coherence; it is not a native minimum or a stability probability. Spatial phase MAD describes variation within the patch, not a motion error bar.
4. Use one candidate explicitly, or **Draw my own reference**. If reference polygons were supplied, a button explicitly says **Replace reference polygons & use**; it removes only those reference features so they cannot silently override the rectangle. Other context features are preserved. A **Restore previous reference polygons** button can undo that replacement during the current exploration.
5. Review the location outside suspected changing ground. Even a coherent, spatially uniform patch may be moving. No land-cover, elevation, atmospheric or GNSS evidence is inferred. The reference remains an assumption unless you independently justify it.
6. Run P04. The selected candidate, assessment ID, quality evidence and limitations are saved with the result. Changed area/files/screening settings are rejected as stale; rerun the assistant or draw your own reference.

The assistant evaluates up to 225 windows and retains up to three separated patches. Each candidate needs at least 25 shared cells and 80% shared coverage; supplied affected areas are excluded. Candidates are ranked by worst-pair median coherence, coverage and spatial phase MAD. Coherence below 0.70 produces a review warning. These thresholds are engineering screens, not universally validated reliability cutoffs. No passing patch means no automatic suggestion; rules are not silently relaxed.

Candidate rate differences are relative to Candidate 1, which is zero by definition. Choosing Candidate 2 subtracts its rate relative to Candidate 1 from a Candidate-1-referenced map. The comparison measures sensitivity of the spatial origin; it cannot determine which ground is stationary. Short/disconnected records can still be assessed for data support, but an unavailable rate comparison is explained.

Assessments are saved in **Your runs** separately from motion analyses. Reopening an assessment does not replace the current area. **Restore this assessment’s saved inputs** explicitly restores matching local files and the science settings; unavailable originals require re-import/search and reassessment. Stored result reference assumptions do not change when you later pick a different reference.

## P04 colors and ranges

| Control | Meaning |
|---|---|
| Rainbow | The 256-color Jet lookup used by the comparison figure, available for signed P04 motion maps. It can exaggerate apparent boundaries; compare with the standard palette. |
| Standard palette | Blue–cream–red for signed motion; quality/class maps keep their own colors. |
| Automatic · shared across dates | Starts from pooled 2nd–98th percentiles of comparable acquired-date frames; signed motion limits are symmetric about zero. Colors keep the same meaning across playback. |
| Automatic · this map only | Starts from this map’s 2nd–98th percentiles; useful for local contrast, but colors cannot be directly compared to separately stretched maps. |
| Full range | All finite values in the active map. Extremes can hide subtle variation. |
| Custom | Explicit finite minimum and maximum in the active layer’s units. Limits must increase; changing units resets to automatic rather than reusing incompatible numbers. |
| Mexico comparison preset | ±30 cm/year or the equivalent ±2.5 cm/month for rate maps only. Other layers fall back to automatic shared ranges with an explanation. |

The displayed clipping percentage reports finite values outside the limits. End colors do not imply equal numeric values beyond the limits. Missing values stay transparent, and numeric GeoTIFF/JSON exports are unchanged. Playback switches per-map automatic/full/Mexico-preset choices to a shared automatic range; custom limits remain fixed while units match. The first reconstructed date is zero by definition and is correctly identified as a constant frame.

## Mozambique GCOV replay (P01)

The **Mozambique paper’s area** preset selects `[32.90, -24.65, 33.14, -24.43]`, GCOV BETA and comparison date 2026-01-17; it preserves launch-to-today discovery dates. For the documented two-date comparison choose the 2026-01-05 and 2026-01-17 track 114 ascending frame 165 X05010 observations only. Save area subsets, or use the existing exact-window subsets. Flood Memory needs no reference area. With these two dates recovery is unavailable; add later observations to investigate an observed return to dry. See [the comparison record](MOZAMBIQUE_FLOOD_COMPARISON.md).


## P03 combined HH/HV change · version 0.7.0

New P03 setups default to combined change: at least three pre-fire baseline dates and one post-baseline date **per viewing group**, both HH and HV. No unaffected reference rectangle is used. Each view uses its own median linear-power baseline; absolute HH and HV dB changes are summed, latest valid views averaged, normalized-Gaussian smoothed (80 m sigma), and robustly standardized across the selected land window. Default candidates use z ≥ 2 and four-connected patches ≥ 10 ha. Native support and missing channels are checked explicitly. Local UTM grids are bounded to 2048 cells per side and four million cells.

The previous reference-relative P03 method remains selectable and continues using the shared reference assistant. Earlier P03 sections describe that method. Combined outputs include a dimensionless change score, candidate mask, view count, individual-view dated magnitudes and signed channel diagnostics. A change candidate is not a burn-severity or recovery measurement. Water, terrain and window selection require review; no DEM/LOS shadow mask is applied. See [the exact protected Timber tutorial](../Examples/P03_Timber_Fire/README.md) for tested dates, settings, real-data agreement and limitations.
