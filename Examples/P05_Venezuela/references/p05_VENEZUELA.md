# Quake Evidence Explorer · Venezuela example

**Current processing: 0.4.3.** See the [overlap investigation and revised maps](P05_OVERLAP_REVIEW.md). Delivered validity masks and shared reference cells resolve the major artifacts of the earlier run. Shared display controls replace the earlier geographical preset labels.

P05 maps **relative line-of-sight displacement across a documented earthquake interval**, in centimeters. It supports a single frame and an explicitly selected coverage mosaic of adjacent tracks/frames. It keeps the original pair measurements and quality evidence available for inspection and download.

## What the NASA example shows

[NASA Earth Observatory’s Venezuela article](https://science.nasa.gov/earth/earth-observatory/where-venezuelas-earthquakes-shifted-the-ground/) describes a centimeter-scale displacement map from acquisitions before and after the June 24, 2026 earthquake sequence. The relevant intervals are **June 13–25** and **June 18–30**. The image legend spans **−50 to +50 cm**, with saturated end colors; the article discusses a larger local value near the coast. That value is not a target to force the application to match.

The image is a visualization with terrain, place names and an inset. It is not a supplied georeferenced numerical validation raster. Its geological east/west interpretation uses viewing geometry and earthquake context. P05 reports relative LOS change without solving separate eastward or vertical components.

## Area and real input records

The old Northeastern Venezuela preset was east of the published region. Its replacement is **Venezuela · NASA earthquake map area**, with approximate bounds **west −69.00°, south 9.80°, east −66.35°, north 11.55°**. These were estimated from the image’s landmarks and scale and are not an official image geotransform. San Felipe, Morón, Valencia, Caracas, La Guaira and the airport are included; substantial ocean areas correctly remain without valid science pixels.

| Track / direction / frame | Pair dates · UTC | Catalog identifier |
|---|---|---|
| 162 / ascending / 006 | June 13 → June 25, 2026 | G4276284486-ASF |
| 162 / ascending / 007 | June 13 → June 25, 2026 | G4276300590-ASF |
| 061 / ascending / 006 | June 18 → June 30, 2026 | G4251306797-ASF |
| 061 / ascending / 007 | June 18 → June 30, 2026 | G4251311930-ASF |

These are production **PROVISIONAL V1 GUNW**, revision **P05023** records discovered in NASA CMR. The application saves native science/quality extracts for the rectangle, retaining exact original filenames, provenance and wavelength. They are genuine NASA measurements, not simulated substitutes. Original files are approximately 2.2 GB each; area-extract size and transferred bytes are separate quantities.

The preset uses the [USGS mainshock record](https://earthquake.usgs.gov/earthquakes/eventpage/us6000t7zp/executive) timestamp, **2026-06-24 22:05:04.053 UTC**. These satellite intervals span the earthquake sequence; they cannot separate the individual shocks or exclude intervening/post-event changes.

## Run it in the application

1. Select the Venezuela example in **Start somewhere**, or use its shortcut in P05’s guided setup. This fills the approximate rectangle, June 13–30 search dates and documented event timestamp. The example chooses an 80 m requested grid, coherence 0.30 and delivered ionosphere subtraction; review these choices before running. A large rectangle is coarsened to fit the 900-cell-per-axis bound, and the actual spacing is reported.
2. Search the **PROVISIONAL** archive for GUNW. View one of the relevant ascending P05023 groups, then choose **Select event coverage across groups**. Review the checked files. At coherence 0.30 in the tested rectangle, the 061/006 record has no usable coherent pixels; uncheck it after reviewing the reported quality failure and use the other three frames. The selector retains the shortest bracketing pair in each matching direction/mode/release group; it does not mix opposite radar views.
3. Save selected-area extracts or complete originals for repeat local use. Existing extracts can be reused through **Use saved data** or imported together using **Import subset folder**.
4. Draw a reference or supply reference polygons, inside the analysis area. Choose independently justified stable ground away from the rupture and expected deformation. Each selected group must contain usable reference ground. At least 25 shared valid analysis cells are preferred for identical reference support across all groups; fallback to independent reference supports is explicitly recorded. Data suitability and coherence do not establish stability.
5. Run **P05 alone** in event-coverage mode. Other tools retain their one-group requirement. Resolve any source-read or reference failure; P05 does not silently drop a selected unreadable source.
6. Inspect **Main results → Displacement across the earthquake interval**. Use **Explore time** to inspect individual measured intervals. Frames can cover different places and dates: playback is source inspection, not a cumulative history.
7. Inspect **Quality & reliability** for reference support, source key, coverage and overlap differences. Use **Advanced maps** for per-group calculations, original mm pairs and interval rates. Every saved layer remains downloadable.

## Calculation and mosaic rules

For each group, delivered valid-sample/subswath and anomaly masks, finite values, coherence and connected components screen native samples before averaging. Packed masks are read losslessly. If requested, the delivered matching radian ionosphere screen is subtracted; other atmospheric/tidal lookup corrections are not assumed to have been applied. Read the saved correction manifest.

The tool chooses the shortest pair strictly containing the event between the **end of its reference acquisition** and the **start of its secondary acquisition**. Original filename windows take priority over catalog bounds. Date-only input excludes boundary days.

Using the delivered radar wavelength in meters:

`relative LOS cm = −wavelength × (phase − median reference phase) × 100 / (4π)`

Positive values mean toward the satellite, negative away. A single view mixes horizontal and vertical displacement. The reference sets an arbitrary relative zero and must be justified physically.

A mosaic processes each group separately, preferring identical fixed reference cells shared across all groups and preserving exact dates. With fewer than 25 shared cells, independent references are explicitly recorded. At overlaps, it chooses the valid source with highest delivered accepted-sample coherence; ties follow sorted group order. No overlap averaging, inferred filling or east/up inversion is performed. The source-index raster identifies every choice. The overlap-spread raster is max-minus-min across available referenced views, not an accuracy estimate. Differences can reflect LOS vectors, acquisition dates, reference choices and processing errors.

## Read the colors and exports

Choose **Diverging** to approximate the published presentation, or **Rainbow** for the same 256-color palette as P04. Use **Custom**, minimum −50 and maximum +50 cm, for a fixed comparison scale; values outside its limits saturate. Automatic, full and custom ranges remain available. White marks the midpoint of the chosen scale, which is zero only for symmetric limits. Transparent/blank areas mean missing evidence rather than zero motion. Inspect the legend and numeric pixels before interpreting colors.

- **Numeric GeoTIFF:** original numeric values, units, missing values and georeferencing; display choices do not alter it.
- **Map image + legend · PNG:** current measurement map, palette/range, dates, source context and reference outline. No photographic basemap; use GeoTIFF for GIS work.
- **Result JSON:** complete source filenames, settings, per-group reference/date table, selection rules, metrics and interpretation limits.

## Comparison and validation boundaries

[ASF’s Urgent Response guide](https://nisar-docs.asf.alaska.edu/urgent-response/) explains that expedited products use forecast orbit information and fewer ancillary corrections, are retained for 30 days, and are followed by production products. The production data currently retrieved need not equal NASA’s original rapid-response processing. The article does not document all its reference, unwrapping, correction and mosaic choices.

The engineering comparison uses a broad inland reference strip **[−68.90, 9.85, −66.45, 10.15]** to give each frame reference support. **Its physical stability has not been independently established.** It is a recorded test choice, not a recommended universal earthquake reference. A changed reference can shift the apparent displacement and create/remove seams. A scientific reproduction should use the original numerical displacement raster, documented reference/corrections and independent geodetic observations.

Synthetic tests check phase-to-cm arithmetic, strict timing, source selection, missing-reference failure, separation of opposite directions/releases, export fidelity and navigation. The completed real-data verification record is stored in [verification.json](../../../docs/validation/p06-venezuela/verification.json) after the real run; its script recomputes referenced phase conversion and mosaic source choices from the retained local extracts. These checks distinguish software correctness from independent geophysical accuracy.

## Earlier real-data check · 0.4.2 · 18 October 2026

The earlier study identifier was **4c623596cf8442de8127a14a7071d11e**. Its metrics below describe the previous processing, not the revised 0.4.3 study. All four native extracts were downloaded and retained. The first four-source run stopped because **061/006** had no coherent connected-component pixels in this rectangle; the final run explicitly uses **061/007, 162/006 and 162/007**. No screening threshold was lowered to force coverage. Processing and independent arithmetic verification read local files only.

| Check | Result |
|---|---|
| Used data | Three genuine production GUNW native extracts from both published date pairs |
| Analysis spacing | 284.1 m after the large-area grid bound; this is not native sensor resolution |
| Mapped cells / area | 281,112 cells / 22,689.10 km²; missing ocean/unsupported cells are retained as missing |
| Overlap support | 2,648.56 km² |
| Overlap LOS difference | Spatial median 2.65 cm; 90th percentile 40.31 cm — differences between views, not accuracy bounds |
| Independent formula/source-selection check | Maximum difference from saved mosaic about 0.0000155 cm; this verifies implementation, not real-world accuracy |
| Software checks | 228 Python tests and 96 frontend tests passed |

The published illustration and the app both show positive values near the western coastal transition and a negative band extending eastward along the coast. The result also contains source-related discontinuities and different local amplitudes. Approximate boxes around the airport/Catia La Mar and La Guaira have negative regional medians, but their exact values are not equivalent to NASA’s local geological displacement figure: the spatial support, LOS quantity, references and processing choices differ. These patterns support a **qualitative regional comparison**, not a pixel-exact reproduction.

The 40.31 cm overlap percentile is substantial and is reported prominently in P05’s reliability explanation. It must not be hidden by palette clipping or interpreted automatically as a real surface boundary. A separate correction-sensitivity check retained the same real input files and reference: applying the delivered ionosphere screen gave a 2.65 cm median overlap difference versus 11.87 cm without subtraction. Upper-percentile differences and valid support also changed, so this does not establish which option is independently accurate. See [correction sensitivity](../../../docs/validation/p06-venezuela/correction-sensitivity.json) and [regional boxes](../../../docs/validation/p06-venezuela/regional-comparison.json).

The annotated image below was visually checked for the map, units, source period, analysis spacing and legend. Live map previews, numeric GeoTIFF downloads and PNG exports were checked through the local API. A fresh interactive browser inspection was unavailable; no browser acceptance is claimed.

[Current published-reference and app-result figures](../README.md#visual-comparison). Historical development figure omitted; the report text below retains the earlier experiment.

[Source-group map](../../../docs/validation/p06-venezuela/venezuela_source_map.png) · [API checks](../../../docs/validation/p06-venezuela/api-checks.json) · [Exact request and excluded-source evidence](../../../docs/validation/p06-venezuela/run-request.json)
