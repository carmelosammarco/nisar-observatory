from pathlib import Path
import json
R=Path(__file__).resolve().parent;O=R/'results';v=json.loads((O/'native-input-verification.json').read_text());c=json.loads((O/'method-comparison.json').read_text());a=json.loads((O/'app-verification.json').read_text())
text=f'''## Completed findings · 20 October 2026

**The real-data workflow works. The result supports a qualitative image comparison, not a validated lava-boundary reproduction.** All five subset hashes match their manifests, product version is 1.0.11, native samples are 10 m, and no nonzero input-data-exception pixels were found in the saved windows. The delivered sample masks still screen the few invalid cells; valid samples do not establish environmental attribution. Stored inputs total **{v['bytes']/1024**2:.2f} MiB**. The evaluation and app run read **zero remote science bytes**.

![NASA and our acquired HH maps, focused on the craters and eastern flows](../../../Examples/P06_Krasheninnikov/references/figures/crater-flow-detail.png)

The double-cone/crater setting, older bright northwest feature and bright finger-like eastern field are recognizable in our acquired HH images. Most of this field is already bright on 18 June. June-to-August departures do not trace that entire existing field: strong increases also appear on broad surrounding slopes and southern/western terrain. That broader pattern is inconsistent with treating the thresholded result as a lava-only map. Snowmelt, wetness and terrain scattering are plausible confounders, but their individual contributions have not been independently measured here. The 3D camera, radiometric/display recipe and exact original source geometries used by NASA cannot be certified from its public video.

Our record samples the later part of the eruption. It does not reproduce the initial crater filling and overflow visible earlier in NASA’s full December-to-August sequence. No temperature, lava volume or deformation in centimetres is derived from these GCOV measurements.

| Quantity on common selected-area support | Result | Interpretation |
|---|---:|---|
| Shared usable area | 478.06 km² | Approximately 100% of selected-window cell centres; rotated grid corners are excluded |
| Latest candidate change · ±3 dB, 40 m sigma, 3 ha patches | 145.60 km² | Brightness change, not lava area |
| Latest same-sign change on ≥2 consecutive later dates | 128.29 km² | Repeat evidence at acquired dates; not continuous persistence |
| Previous all-later-dates classification formula | 66.99 km² | Stricter temporal intersection on unsmoothed values; not an accuracy benchmark |
| New-method dated candidate objects | 690 | Overlap-linked components, not 690 physical lava flows |

| Signed threshold · fixed smoothing and patch area | Latest candidates · km² | Repeated latest candidates · km² |
|---|---:|---:|
'''
for x in c['threshold_sensitivity']:text+=f"| ±{x['threshold_db']} dB | {x['latest_change_area_km2']:.2f} | {x['repeated_latest_change_area_km2']:.2f} |\n"
text+='''
The roughly twofold candidate-area difference between 2 and 4 dB shows substantial setting sensitivity. It is not a confidence interval. The larger result from the new method is not evidence of higher lava-mapping accuracy: the smoothing, physical patch filtering and latest-date rule differ from the previous method.

**Previous-method resource limit:** its complete object-tracking step exceeded the existing 1,000-object safety cap on these unsmoothed dates. The application cap was not raised. The comparison raster uses the exact previous numerical classification formula after the same geographic clipping; it is explicitly labelled a formula-only comparison, not a successfully completed legacy tracking run. The new method completes normally with 690 objects.

![Same-grid method comparison](../../../Examples/P06_Krasheninnikov/references/figures/processing-comparison.png)

## What changed in P06 and the shared experience

- Late-growing features are retained. Latest, first observed and repeated evidence now answer separate questions; the previous method remains selectable for historical recipes.
- Native quality is retained and analysis-cell centres outside the selected geographic rectangle are excluded from the rotated UTM envelope.
- The corrected volcano preset supplies geography and the tested settings. Mission-wide search dates remain intact. Initial P06 selection adds an available baseline observation when the four latest files would omit it; preparation explains missing baseline/later data.
- Smoothing reuses P03’s shared helper/control without changing its scientific calculations. Case-specific baseline-end dates are cleared when selecting unrelated area presets.
- First-change dates have explicit index/date keys in the result and PNG; pixel inspection translates date indices to dates or intervals.
- Moving between raw brightness and signed brightness change resets a custom range, even though both use dB. A shared automatic brightness range makes acquired dates comparable. The saved main-map view uses Diverging, −8 to +8 dB; the numeric rasters retain values beyond those endpoints.

## Application verification

'''
text+=f"Browser-created run **{a['job_id'][:8]}** completed with all five local files; its metrics exactly equal the local study. All **{a['layers_verified']} registered map previews** and their georeferenced float32 rasters were checked. Standalone main-map and first-change PNGs contain legends and provenance; the first-change legend shows acquisition dates. A downloaded numeric GeoTIFF matches its saved file byte for byte. Reopening from Runs restores the signed-change map, Diverging palette and ±8 dB limits. Date exploration resets to a shared brightness scale, approximately −17.72 to −2.36 dB.\n\n"
text+='''![Verified browser result](../../../Examples/P06_Krasheninnikov/references/figures/browser-p06-result.png)

[App verification receipt](results/app-verification.json). Engineering regression: **306 Python tests and 165 browser-logic tests passed**. These checks establish software behavior, not lava-classification accuracy. The API checks cover actual local data; the browser walkthrough covers preset selection, five-file selection, settings, preparation, execution, reopening and brightness-date exploration. Existing five protected Examples remain unchanged.

## Recommendation before an Example

Keep the new P06 surface-scattering workflow and the acquired-image comparison. **Do not describe this case as a validated lava-area map or an exact NASA reproduction.** A quantitative volcanic-flow Example needs independently georeferenced dated flow boundaries and stronger separation of seasonal/background changes, potentially using coherence and independent optical/thermal evidence. No extra satellite downloads were made for those future possibilities. The present study stays outside Examples pending user review.
'''
p=R/'README.md';s=p.read_text();start=s.index('## Interpretation and decision');end=s.index('## Reproduce locally',start);s=s[:start]+text+'\n'+s[end:];s=s.replace('The evaluation saves:','The completed evaluation saved:');s=s.replace('It verifies all five file hashes, reads only local subsets, processes both methods on the same grid and exports the evidence.','It verifies all five file hashes, reads only local subsets, runs the evolving method, attempts the previous method with an explicitly labelled formula fallback at its tracking cap, and exports the evidence on the same grid. Run `plot_comparison.py` to regenerate the figures.');p.write_text(s)
