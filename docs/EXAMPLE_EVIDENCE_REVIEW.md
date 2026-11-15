# Seven-example evidence review

The reviewed question is whether each example gives a defensible demonstration of tracking and visualizing surface change, and what its comparison actually establishes. Review scope: the seven existing cases, unchanged real protected inputs and processing settings, source/reference provenance, quantities, periods, coverage, numeric comparisons and presentation. No new satellite downloads or new detection methods were introduced.

## Recommended demonstration

**Lead: Timber Fire → supporting: Mozambique → supporting: Mexico City.** This is a demonstration recommendation, not an accuracy ranking between different measurements. Timber has the strongest inspectable numerical case evaluation, Mozambique has the clearest two-date story, and Mexico shows ground-motion measurements from a different product. Samudra Tapu remains a useful deeper geometry example; the unmatched reference period and vertical-motion constraint make it weaker as an opening accuracy claim.

| Case | Evidence available | Demonstration role | Main limit |
|---|---|---|---|
| [Chókwè flood, Mozambique](../Examples/P01_Mozambique/README.md) | Qualitative event comparison | Supporting demonstration · 2 | No georeferenced independent water mask or field labels: no justified precision, recall or IoU. |
| [Wheeler Marsh, Connecticut](../Examples/P02_Wheeler_Marsh/README.md) | Method adaptation with tide context | Further exploration | Spearman 0.829 for six observations is descriptive association, not accuracy or causation; no independent test set is supplied. |
| [Timber Fire, California](../Examples/P03_Timber_Fire/README.md) | Quantitative single-case comparison | Lead demonstration · 1 | An incident perimeter is an operational proxy that can include unburned islands; precision here is not a universal burned-pixel accuracy. |
| [Mexico City, Mexico](../Examples/P04_Mexico_City/README.md) | Qualitative motion-pattern comparison | Supporting demonstration · 3 | No independent co-registered velocity grid or GNSS measurements: no justified RMSE or speed-accuracy percentage. |
| [Venezuela earthquake sequence](../Examples/P05_Venezuela/README.md) | Qualitative event-interval comparison | Further exploration | No numerical NASA displacement raster or independently stable reference: no justified pixelwise accuracy statistic. |
| [Krasheninnikov, Kamchatka](../Examples/P06_Krasheninnikov/README.md) | Qualitative scattering comparison | Further exploration | No independent dated flow polygons: no lava precision, recall, IoU or lava-area estimate. |
| [Samudra Tapu, Himalaya](../Examples/P07_Samudra_Tapu/README.md) | Conditional velocity-pattern comparison | Further exploration | No contemporaneous co-registered independent velocity raster: no justified RMSE or accuracy percentage. |

## Three checks that must not be conflated

1. **Input integrity:** checksums identify the expected files; they do not establish that a physical interpretation is correct.
2. **Implementation reproducibility:** unchanged guided and editable workflows reproduce recorded values. These paths share scientific kernels and inputs, so their agreement is not independent environmental validation.
3. **External evaluation:** appropriate external labels/measurements must have comparable quantity, dates, reference and spatial support. A numerical proxy comparison is still conditional on the proxy. Paper figures, common sensor inputs and similar maxima do not supply universal accuracy.

Each tutorial now has the same assessment: what agrees, what differs, what is unverified and the next useful validation. Every tool has shared guidance on the calculated measurement, colours, quality checks and limits. Saved new result JSON carries this interpretation; old saved runs are displayed without rewriting their values. Modified workflow outputs do not inherit the example’s evidence.

## Timber Fire: independently checked arithmetic and fresh spatial evaluation

The archived confusion counts independently reproduce precision **0.9964846**, recall **0.7243652**, F1 **0.8389096** and official-perimeter IoU **0.7225188**. Against the author output, IoU is **0.9643458**. These are different reference targets.

The fresh replay reads the actual exported candidate and score rasters and rasterizes both archived vector boundaries on that grid. All **45,228.56 ha** of finite radar support are eligible. The official-perimeter results retain those same precision/recall/F1/IoU values, with AUC **0.9861685**. The historical evaluation used **45,208.76 ha** of common radar/optical cells and AUC **0.9862305**. The additional 495 true-negative radar cells explain the small AUC change; no candidate patch changed. The optical-validity raster is not bundled, so the historical AUC is not presented as freshly recomputed.

The official incident boundary is external operational evidence and can include unburned islands. Author-output agreement is method reproduction using the same NISAR observations. Neither is independent field burn severity, a held-out test or certification for other fires. Land/window/mask differences remain disclosed.

[Calculation protocol, boundary SHA-256 and full counts](validation/example-evidence-review.json) · [Archived historical comparison](../Examples/P03_Timber_Fire/references/integrated-comparison.json).

## Quantity and time checks

- **Mozambique:** new water candidates in a small north-up rectangle versus wider NASA flood/polarimetric imagery. Two dates cannot establish recovery. Candidate area is strongly threshold-dependent. Newly appearing candidates (90.47 km²) differ from the approximate net candidate-area increase (75.49 km²), because other cells lose their candidate label.
- **Wheeler Marsh:** historical PALSAR inundation/depth methods versus six 2026 NISAR water-candidate snapshots. Nearby tide association is context, not contemporaneous pixel accuracy or continuous hydroperiod.
- **Timber Fire:** unsigned combined HH/HV change and thresholded candidates versus an official perimeter/author output. Two radar directions have different latest dates. The result is not burn severity or recovery.
- **Mexico City:** the article discusses monthly rates while the published figure and app opening use annual rates. Divide cm/year by 12 for cm per mean month; an 84-day fitted LOS record does not become a full year or a vertical subsidence measurement. Reference stability is not independently established.
- **Venezuela:** event-bracketing LOS intervals and viewing groups versus an interpreted NASA displacement illustration. A coverage union is not a common footprint. Overlap spread is internal consistency, not an accuracy bound or building-damage measure.
- **Krasheninnikov:** five-date baseline-relative scattering changes versus a longer oblique brightness animation. June already contains lava; snow/wetness are not separated and no lava-area accuracy is reported.
- **Samudra Tapu:** one exact 12-day, zero-vertical-motion horizontal estimate versus a study giving January rather than exact pair IDs and a multiyear ITS_LIVE comparison. Historical glacier extent and partial support are explicit; similar extrema are not pixelwise validation.

## Source verification and access limits

Primary pages were checked on 23 October 2026 where accessible. Their interpretation is kept within their stated quantity and period. The bundled references, figures and earlier comparison reports supply the historical case evidence; access failures are not treated as new verification.

| Case | Primary source and current access | Consequence |
|---|---|---|
| Mozambique | [NASA SVS 5661](https://svs.gsfc.nasa.gov/5661/) accessible | Dates, false-colour channels and wider visualization confirmed; no numerical water mask or exact classifier supplied. |
| Wheeler Marsh | [Historical study](https://doi.org/10.3390/rs17020263), [later method](https://doi.org/10.3390/rs18081172): publisher access returned throttling/access errors | Existing archived method/tide records reviewed; full papers not freshly reread. Do not transfer their published accuracy to this NISAR run. |
| Timber Fire | [SSRN preprint](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7553393): indexed author abstract accessible; full delivery returned access errors | Prior archived full-paper review and Figure 5 retained; this pass independently checks actual app outputs and archived boundary vectors, not a fresh full-text reread or live boundary refresh. |
| Mexico City | [NASA/JPL article](https://www.jpl.nasa.gov/news/us-indian-space-mission-maps-extreme-subsidence-in-mexico-city/) accessible | Comparison dates, monthly narrative and residual-noise discussion checked; no numeric reference grid extracted from the picture. |
| Venezuela | [NASA Earth Observatory article](https://science.nasa.gov/earth/earth-observatory/where-venezuelas-earthquakes-shifted-the-ground/) accessible | Observation intervals, LOS mixture and preliminary response-processing context checked. |
| Krasheninnikov | [NASA/JPL article](https://www.jpl.nasa.gov/news/us-india-satellite-captures-time-lapse-video-of-volcanic-eruption/) accessible; [SVS 5675](https://svs.gsfc.nasa.gov/5675/) returned a service error | Use the accessible narrative and archived dated frames; do not infer a numerical lava mask. |
| Samudra Tapu | [IIRS study](https://science.iirs.gov.in/nisar-for-monitoring-glacier-motion/) accessible | January 2026 ranges and multiyear ITS_LIVE reference checked; exact pair/conversion/time-aligned reference remain unspecified. |

## What was not done

No new external download, held-out event study, novice-user experiment or independent ground survey was performed. Scientific calculations and numeric exports were preserved. Broader transfer validation remains future work, rather than a claim added by clearer wording.
