# Wetland Pulse · Wheeler Marsh real-data comparison

> **Historical baseline:** this record preserves the original single-channel run and separate diagnostic. The HH/HV method is now integrated in app 0.4.9; see [the current replay and comparison](P02_HH_HV_COMPARISON.md). References below to an unintegrated diagnostic describe the earlier study.

**Study date:** 18 October 2026 · **Application:** 0.4.8 · **Algorithm:** 0.4.0  
**Saved analysis:** `0abb2d9e13ba4c3f96f908c26743f780` · **Download job:** `fc04f323cfcb46fe934e8fda909caeac`

## What this test establishes

**Ready for exploratory use, with scientific caveats.** Six real NISAR GCOV area subsets were downloaded and processed successfully. Direct source-array recalculation matches the saved maps, areas and zone statistics. No satellite scene is synthetic or silently omitted.

**The default classifier is not yet a validated tidal-marsh inundation method.** Its candidate-water area has a weak rank association with nearby measured water level across these six dates (Spearman ρ = 0.314). A separate adaptation of the published HH/HV thresholds gives a stronger association (ρ = 0.829), but neither value is classification accuracy. This diagnostic has not replaced the app's saved P02 processing.

## The published benchmark

[Lamb et al. (2025)](https://doi.org/10.3390/rs17020263), especially Figure 6, maps Wheeler Marsh inundation from historical PALSAR L-band imagery using HH/HV thresholds and compares classifications with sensor-derived inundation states. It reports 90% accuracy for that comparison (54/60). This is a reference for the method and expected spatial response, not a score for our app.

[Lamb et al. (2026)](https://doi.org/10.3390/rs18081172) extends the approach with elevation data and calibrated synthetic tide gauges to estimate depth and volume. Those outputs are outside the current P02 calculation. Its published radar scenes are also historical PALSAR, not our NISAR dates.

USGS describes [current Milford sensor deployments for NISAR calibration/validation](https://eros.usgs.gov/doi-remote-sensing-activities/2025/usgs/coastal-inundation-monitoring-nisar). We did not obtain contemporaneous in-marsh inundation labels from those deployments. The public [field-data release](https://doi.org/10.5066/P149ZGMQ) describes observations from August–December **2018**, despite its 2026 release date; these are not direct 2026 truth.

## Area and inputs

The app preset is now **Wheeler Marsh paper's area**, replacing Camargue. Its WGS84 extraction rectangle is west **−73.130**, south **41.160**, east **−73.080**, north **41.210**. This includes the published site and surrounding estuary; it is **not the exact paper boundary**.

The comparison uses [official NWI inventory polygons](https://www.fws.gov/program/national-wetlands-inventory/web-mapping-services), independently selected before inspecting radar results. Every estuarine emergent polygon (`ATTRIBUTE` begins `E2EM`) intersecting the window is clipped and dissolved. Two zones use the regularly flooded `N` and irregularly flooded `P` inventory categories. This also includes some adjacent mapped marshes, not only the paper's exact study polygon. The source imagery vintage was not established in this test.

The vector domain covers approximately 2.861 km²; its cell-centre rasterisation contains **2.8648 km² / 7,162 cells** on the 20 m equal-area grid. All domain cells have common support on all six dates. Grey outside the polygon is excluded land/water, not missing satellite coverage. Tiny vector/raster area differences arise from grid boundaries and 2 m topology-preserving polygon simplification.

All sources share **GCOV PROVISIONAL · track 133 ascending · frame 022 · mode 4005 · HH/HV · P05023**. Native Frequency A spacing is 10 m; the saved analysis grid is **20 m**, EPSG:6933, 242 × 242 cells. Regridding does not create finer observations.

| Acquisition | NASA CMR granule | Native pixel spacing | Saved subset · MB |
|---|---|---|---|
| 2026-08-10 | [G4277063540-ASF](https://cmr.earthdata.nasa.gov/search/concepts/G4277063540-ASF.json) | 10 × 10 m | 2.81 |
| 2026-08-22 | [G4288404845-ASF](https://cmr.earthdata.nasa.gov/search/concepts/G4288404845-ASF.json) | 10 × 10 m | 2.81 |
| 2026-09-03 | [G4298883436-ASF](https://cmr.earthdata.nasa.gov/search/concepts/G4298883436-ASF.json) | 10 × 10 m | 2.81 |
| 2026-09-15 | [G4314046400-ASF](https://cmr.earthdata.nasa.gov/search/concepts/G4314046400-ASF.json) | 10 × 10 m | 2.81 |
| 2026-09-27 | [G4327549825-ASF](https://cmr.earthdata.nasa.gov/search/concepts/G4327549825-ASF.json) | 10 × 10 m | 2.81 |
| 2026-10-09 | [G4357432044-ASF](https://cmr.earthdata.nasa.gov/search/concepts/G4357432044-ASF.json) | 10 × 10 m | 2.81 |


**Storage:** 16.87 MB in six native HDF5 subsets, in `data/subsets/GCOV_2026-10-18_20-11-41_UTC/`. The source archive transferred 247.0 MiB of compressed blocks/metadata. No complete multi-gigabyte original was downloaded. Subsets retain both polarisations, source masks and the gamma-to-sigma factor and can be imported as one folder.

## Tide screening and date choice

We screened all 11 compatible May–October acquisitions in the selected group using [NOAA Bridgeport station 8467150](https://www.tidesandcurrents.noaa.gov/stationhome.html?id=8467150), checking measured levels as well as predictions. The six dates form a relatively compact 60-day sequence, all 12 days apart, spanning approximately **1.43 m** of measured water-level difference. Avoiding a winter-to-summer series reduces one source of phenological confounding; this does not remove seasonal or weather effects.

Satellite times are approximately **09:59 UTC**. Levels are linearly interpolated from bracketing six-minute NOAA samples at the scene midpoint; local pixel timing within the approximately 33-second scene was not reconstructed. **All heights below are relative to NAVD88**, not water depth in the marsh. Negative heights mean below the datum, not negative water depth. Five dates are NOAA verified (`q=v`); 9 October is preliminary (`q=p`) and may change.

| NISAR date · 2026 | Measured level · m NAVD88 | Predicted level · m NAVD88 | Gauge quality | Saved P02 candidates · km² | Separate HH/HV diagnostic · km² |
|---|---|---|---|---|---|
| 08-10 | -0.375 | -0.440 | Verified | 0.0900 | 0.2548 |
| 08-22 | +0.562 | +0.345 | Verified | 0.2412 | 0.5064 |
| 09-03 | +0.660 | +0.437 | Verified | 0.1060 | 0.6784 |
| 09-15 | -0.043 | -0.190 | Verified | 0.1260 | 0.3044 |
| 09-27 | -0.186 | -1.120 | Verified | 0.0104 | 0.1228 |
| 10-09 | -0.773 | -0.901 | Preliminary | 0.1076 | 0.2460 |


**Do not use predictions alone:** on 27 September the measured level was about **0.934 m above prediction**. NOAA also recorded **7.4 m/s wind with 15.5 m/s gusts** near the overpass, compared with approximately 0.9–2.1 m/s on the other five dates. Weather-related water-level departures and wind roughening are plausible confounders; these readings do not prove the cause of any mapped difference. Wind evidence is retained separately.

The published work uses a local tidal-lag correction and calibrated marsh-specific water-level relations. We did **not** equate Bridgeport levels to marsh depth or apply an uncalibrated regression. Shifting gauge sampling by ±15 minutes gives default-classifier ρ values of 0.314 and 0.486; this does not resolve its weak association. Excluding the preliminary October reading leaves five dates: default ρ = 0.600, separate diagnostic ρ = 0.900. These are small-sample descriptive checks, not significance or accuracy claims. No full tidal cycle or annual hydroperiod is sampled.

### All screened growing-season dates

| Candidate date | Measured water level · m NAVD88 | Used |
|---|---|---|
| 2026-05-06 | -0.088 | No |
| 2026-05-18 | -1.182 | No |
| 2026-05-30 | -0.904 | No |
| 2026-06-11 | +0.414 | No |
| 2026-07-17 | -0.392 | No |
| 2026-08-10 | -0.375 | Yes |
| 2026-08-22 | +0.562 | Yes |
| 2026-09-03 | +0.660 | Yes |
| 2026-09-15 | -0.043 | Yes |
| 2026-09-27 | -0.186 | Yes |
| 2026-10-09 | -0.773 | Yes |


## What the saved P02 run actually calculates

1. Read the six saved local HDF5 windows, selecting HH power, with native validity screening before averaging. All inspected `inputDataExceptionMask` values are zero.
2. Average valid **linear gamma-zero power** onto the common 20 m grid, requiring at least 50% accepted native contribution per cell.
3. Apply the independent NWI domain. Convert positive power to decibels with `10 log10(power)`.
4. Classify a candidate wherever HH gamma-zero is **below −17 dB**, unchanged across dates. This is the existing default, not a threshold fitted to these tides.
5. Count detections across the six acquired dates on fixed common support; compare named zones and calculate threshold/grid sensitivity and dated patch histories.
6. Save maps, source/setting provenance and exports. The opening occupancy view uses **0–1**; dated candidate classes use the same fixed colours on every date.

The optional cross-polarisation contrast was enabled, but it does **not** turn the saved P02 classifier into the paper's HH/HV joint classifier. The ±1 dB ambiguity layer flags near-threshold values; the occupancy calculation still uses the declared hard threshold. The 30,000 m² minimum patch area filters tracked candidate objects, not the unfiltered pixel-area totals or occupancy map.

## Results and how to read them

Within the fixed 2.8648 km² inventory domain, candidate water ranges from **0.0104 km²** on 27 September to **0.2412 km²** on 22 August. At least one but not all observations classify water over **0.3544 km²**. No cell meets the water rule on all six dates. This does **not** establish that the marsh is dry or that persistent water is absent: this strict classifier may miss vegetated inundation.

| Date | Regularly flooded inventory zone · candidates | Irregularly flooded inventory zone · candidates |
|---|---|---|
| 2026-08-10 | 9.92% | 0.02% |
| 2026-08-22 | 25.48% | 0.57% |
| 2026-09-03 | 10.72% | 0.47% |
| 2026-09-15 | 13.87% | 0.04% |
| 2026-09-27 | 1.11% | 0.02% |
| 2026-10-09 | 11.83% | 0.04% |


[Current published-reference and app-result figures](../README.md#visual-comparison). Historical development figure omitted; the report text below retains the earlier experiment.

[Current published-reference and app-result figures](../README.md#visual-comparison). Historical development figure omitted; the report text below retains the earlier experiment.

Each 1/6 frequency step represents one satellite observation, not ten days or a fraction of every tidal cycle. The inventory zones are habitat categories, not labels inferred from the radar. Greater candidate frequency in the regularly flooded zone is qualitatively reasonable, but does not validate individual pixels. Baseline/latest totals alone miss the intermediate pulse.

## Comparison with the published method

| Aspect | Published Wheeler work | Saved Wetland Pulse run | Consequence |
|---|---|---|---|
| Observations | Historical PALSAR, published study dates | Six new 2026 NISAR observations | Same broad site and hypothesis, not a same-date map replay |
| Water rule | HH sigma-zero < −14 dB **and** HV sigma-zero < −23 dB | HH gamma-zero < −17 dB | Different variables and decision boundaries; maps should not be expected to match |
| Filtering/support | Study-specific filtering, registration and marsh boundary | Valid-power averaging to 20 m; independent NWI domain | Mixed pixels, noise and boundary differences remain |
| Reference evidence | In-marsh sensors and calibrated gauge relations | Nearby gauge observations; no contemporaneous marsh labels | No independent confusion matrix, accuracy, IoU or recall can be reported |
| Depth/volume | Follow-up combines elevation and water-level modelling | Not calculated | Frequency and candidate area cannot be read as water depth or storage |

For a **separate diagnostic**, the delivered gamma-to-sigma factor was multiplied into native linear HH and HV power **before** averaging; both published thresholds were then applied. The factor's native grid and description were inspected. [ASF documents this factor and GCOV radiometry](https://nisar-docs.asf.alaska.edu/gcov/). The joint rule uses the same 2.8648 km² common support as the primary run. It omits the paper's Enhanced Lee filtering, elevation analysis and calibrated tide models. Its thresholds are not independently calibrated for these NISAR scenes.

The diagnostic gives 0.1228–0.6784 km² of candidates, and stronger tide association (ρ ≈ **0.83**, versus **0.31** for saved P02). On the highest measured-level date, 3 September, it maps **0.6784 km²**, compared with **0.1060 km²** in the saved app run. This is evidence that the classifier choice matters, **not evidence that all additional pixels are correctly flooded**.

[Current published-reference and app-result figures](../README.md#visual-comparison). Historical development figure omitted; the report text below retains the earlier experiment.

These bottom-row maps are **our diagnostic**, not the paper's historical images. For the published maps see Figure 6 of the 2025 paper and Figure 3 of the 2026 paper. A numerical map-to-map accuracy comparison against those different-date PALSAR scenes would be misleading.

## Sensitivity: avoid choosing a threshold just to match the gauge

| HH gamma-zero threshold | 22 August candidates · km² | 3 September candidates · km² | Gauge association · Spearman ρ |
|---|---|---|---|
| -19 dB | 0.0192 | 0.0052 | 0.464 |
| -18 dB | 0.0904 | 0.0248 | -0.086 |
| -17 dB | 0.2412 | 0.1060 | 0.314 |
| -16 dB | 0.3936 | 0.2684 | 0.714 |
| -15 dB | 0.5156 | 0.4968 | 0.771 |


For 22 August, changing −17 dB by ±1 dB changes candidate area from **0.0904 to 0.3936 km²**, versus 0.2412 km² at the declared default. Less restrictive thresholds follow the gauge more closely in this sample, but selecting them using these same six dates would be tuning to the evaluation set. It would not demonstrate accuracy. The original −17 dB results are retained.

## Recommended next step

Keep this as an auditable exploratory baseline. Before presenting P02 as a validated inundation product, obtain date-matched in-marsh labels (or defensible calibrated sensor/gauge models), assess HH/HV sigma-zero classification and filtering, calibrate on separate dates/locations, then evaluate on withheld observations. Check local tidal lag, source noise, wetland boundaries, vegetation and weather. More favourable gauge correlation alone is insufficient. No new classifier or depth/volume capability was silently added to the application.

## Open or reproduce the result

1. In **Runs**, open **Wetland Pulse · completed**, run beginning **`0abb2d9e`**. The main result is the observed water-candidate frequency map. The saved opening scale is 0–1.
2. Use **Explore time** for the six acquired snapshots and the named-zone chart; playback advances only through observations. **Quality & reliability** contains support, source contributions and sensitivity evidence. All 41 saved layers remain downloadable as GeoTIFF, with JSON provenance and PNG map/legend exports.
3. To recreate it, choose **Wheeler Marsh paper's area**, use saved data (or import the whole subset folder), and select the six dates in the group listed above. Search defaults remain launch through today; narrow the search manually if convenient.
4. Review **20 m**, **−17 dB**, **0.5 native valid fraction**, and optional cross/co-polarised contrast. The preset does not overwrite shared quality choices.
5. In the tool's detail card, choose **Download named wetland zones**, then import it under **Area & analysis settings → Advanced options → Spatial context**. Without this file, the rectangle includes permanent river/sea water and the chart uses geometric halves; it is a different analysis.
6. Run Wetland Pulse. **Reuse this setup** on the existing run restores its saved options and polygons, avoiding a manual re-entry.

The app was restarted to activate the changed guide and notes. Its Earthdata session was erased as designed; saved subsets and this local analysis do not require reconnecting.

## Verification and evidence

**Engineering:** 290 backend tests and 134 interface tests passed, with one existing test-client deprecation warning. Relevant interface checks were rerun after the example-card/coverage-note changes. The real run has no source errors. Direct HDF5/reprojection recalculation, SHA-256 checks, per-date classes, occupancy, equal-area metrics and named-zone statistics all agree. These checks establish computation integrity, not environmental accuracy.

Browser review confirmed the new preset and exact rectangle, tool instructions and named-zone download link, the saved run's 20 m grid and 0–1 opening scale, all six dated views, next-frame navigation and playback reaching the sixth date. No physical mobile-device review is claimed.

Evidence is organised under [`docs/validation/wheeler-marsh/`](../../../docs/validation/wheeler-marsh): `sources/` holds catalogue, NOAA and NWI receipts; `tide-screening.json` records every screened acquisition; `wind-context.json`, `context-provenance.json`, `verification.json`, `result.json` and the job records retain inputs and checks. Figure files are derived from real arrays. `paper-inspired-diagnostic.npz` is separately labelled diagnostic evidence, not an official NISAR product or app classification mode.

Reproduction helpers are `scripts/prepare_p02_wheeler.py`, `scripts/wheeler_context.py`, `scripts/run_p02_wheeler.py` and `scripts/verify_p02_wheeler.py`. They do not contain Earthdata credentials. Public reference evidence does not require authentication; satellite downloads use the running app's RAM-only session.
