# Tool discovery, P04 guidance and map-image exports

This presentation update keeps the 10 focused scientific processors. It organizes access to them and adds presentation images; it does not change the processing algorithms or establish accuracy in a new region.

## Choose a question, then prepare the evidence

| Theme | Experiences | Typical starting point |
|---|---|---|
| Water & wetness | P01 Flood Memory, P02 Wetland Pulse | Compatible GCOV observations |
| Land & vegetation | P03 After Fire Observatory, P06 Volcano Surface Diary | GCOV trajectories and context |

The Explore Earth tool list uses the same four groups. The Tools page adds question/name/input search and a product filter. Each card states the question, minimum observations, extra inputs and first result to inspect. The two actions have separate purposes:

- **Set up this tool** takes you to guided inputs and the existing pre-run checks.
- **Method & evidence** opens the implemented method, outputs, interpretation limits, product documentation, papers and real examples.

Every method and successful-result page has a consistent Prepare → Start here → Interpret carefully guide. The guide is a reading path, not a new classifier or a claim that the environmental interpretation is validated. Existing detailed scientific evidence remains available.

## Sinking City Atlas: three clear steps

1. **Choose connected observations.** One GUNW pair gives a relative interval map. A rate needs at least two connected pairs linking three dates; four or more dates over several weeks give a better starting record. A shared acquisition links pairs. Disconnected intervals cannot establish one connected history.
2. **Choose and justify a reference.** The assistant compares data suitability, shared support, coherence and reference-choice sensitivity. It does not prove stability. Alternatively draw a reference within the study area, avoiding the suspected changing zone. Use the reference-support map to see the cells actually used across the selected observations.
3. **Read rate, history and quality together.** The rate summarizes the observed record in cm/year or cm/month. Acquired-date playback shows reconstructed accumulated relative change in cm, with the first date fixed to zero. Pair intervals remain separate measurements. Inspect coherence, fixed reference support and fit diagnostics; fit residuals measure internal consistency rather than independently established accuracy.

Positive LOS is toward the satellite; negative LOS is away, relative to the reference. Vertical and horizontal movement can contribute. An annualized short record does not become a year of observations.

The setup dialog keeps this path visible and places specialist revision-comparison controls in an Advanced section. Current grid, coherence and ionospheric correction choices remain explained. The scientific defaults and calculations have not been changed by this presentation update. Missing correction screens still require an explicit user decision; no correction is silently guessed.

## Read results in four sections

Every tool opens on **Main results**, with **Explore time**, **Quality & reliability** and **Advanced maps** as separate choices. Each selection explains what it measures and what cannot be inferred. Empty categories are disabled. Historical runs show their available saved outputs; no science layers are created by this navigation.

| Tool | Main views when available |
|---|---|
| P01 Flood Memory | Comparison-date water, first observed return to dry, unresolved new-water candidates |
| P02 Wetland Pulse | Candidate-water observation frequency |
| P03 After Fire Observatory | Reference-normalized scattering change |
| P04 Sinking City Atlas | Relative motion rate and total observed-period change; interval results when no fitted history is available |
| P05 Quake Evidence Explorer | Event-interval LOS displacement in cm; explicit adjacent-group coverage mosaic when selected |
| P06 Volcano Surface Diary | Latest departure, latest changed patches, repeated evidence and first-change dates; previous method retained |
| P07 Glacier Motion Pulse | Change between interval rates and rate variability; a single interval shows its measured rate |

Dated frames belong to **Explore time**. Reference support, valid counts, threshold sensitivity, screening and fit residuals belong to **Quality & reliability**. Baselines, original measured pairs and alternative calculations belong to **Advanced maps**. An event-bracketing frame can also be the main finding; opening playback deliberately switches to Explore time.

For fitted P04 results, one **Relative motion rate** view has a cm/year or cm/month selector. The selector uses the existing saved rate layers; monthly values and custom endpoints equal annual values divided by 12. It updates the preview, legend, numeric GeoTIFF link and PNG export consistently. Failure to load a new unit restores the previous unit and limits. Acquired-date accumulated change stays in cm. Rates remain relative LOS quantities rather than direct vertical subsidence.

The grouped result views are the only layer selector. Main results, acquired dates, quality diagnostics and advanced outputs remain available, including alternate rate units. Display a layer, then use the shared map-adjacent PNG/GeoTIFF buttons. The redundant flat catalogue has been removed without deleting any scientific layer or file.

### Navigation verification

The earlier navigation verification passed **91 tests**. It checks all ten processor-output inventories generated from explicitly synthetic observations, complete layer retention, main-view prioritization, category navigation, event-frame aliases, explanations, unit rollback and custom-limit conversion. An integrated test exercises the actual preview selection and map-export link code for P04 units. Scientific calculations are unchanged. No new real-region accuracy assessment or browser visual inspection is claimed by these tests.

## Download a map with its color scale

After a successful run, choose a main, quality, advanced or acquired-date map, then apply the desired palette/range. Use **Map image + legend · PNG** alongside the numeric GeoTIFF download. The link follows the last successfully displayed map, including custom endpoints and the P04 Rainbow choice. Playback updates the link with the displayed frame; click it when the desired frame is visible.

The backend resolves the same layer and display options as the map preview. It does not re-run the scientific processor. It produces a lossless 1800 × 1570 RGB PNG with 200 dpi print metadata, including:

- Tool and layer titles, units and applied palette.
- Measurement image with north direction and longitude/latitude coordinate ticks; display aspect ratio follows its Web Mercator bounds.
- A matching numeric gradient for continuous quantities or meaningful class swatches for water states, binary masks, gain/loss classes and patch IDs.
- UTC observation/record period, source count and count of area-extract inputs.
- Actual analysis cell spacing, explicitly distinguished from native sensor resolution.
- Processing-reference context retained in provenance; automatic reference boxes are omitted from the PNG.
- Clipped-value percentage, no-data key, run identifier, algorithm version and interpretation notes.
- Embedded PNG metadata containing layer details, exact scale/palette, available mapped class/date labels, grid, source IDs/names/date intervals and interpretation.

Observation-index maps such as first observed dry state use date labels from the saved index calendar when available; indices are not elapsed days. Large categorical/date legends show up to eight representative entries, with the limit stated and remaining entries retained in PNG metadata and the result JSON. Patch colors identify objects rather than severity.

The default PNG contains the measurement layer alone, with opaque measurement colours matching the legend. Tick **Include background** beside the PNG link to include the selected background, current optional place-name choice and map radar opacity. **PNG area** chooses **Full result area** or **Current map view · zoom & surroundings**. Current view captures the visible geographic bounds at download time and crops/pads the display with nearest-neighbour sampling; surrounding context appears when Include background is on. The colour range remains the active range, including when no radar observations fall inside the current camera. Both extents use exact Web Mercator alignment and retain the full colour scale, legend and source credits. Streets contains labels within its tiles; the other background styles follow the place-name switch. On background exports, missing radar cells reveal the basemap and are explained as missing measurements. A failed online background produces an actionable message, with raster-only export still available. On raster-only exports, category opacity is preserved against a neutral page background and recorded in the key and PNG metadata. Transparent valid categories reveal that neutral page; genuinely missing observations retain the checker pattern. Blank/invalid values use a distinct checker background. No artificial spatial smoothing is added during image enlargement. The geographic map scale varies with latitude in Web Mercator; the color scale always states the measurement units.

**PNG is not georeferenced.** Continue to use the numeric GeoTIFF for GIS analysis and the JSON for the complete processing record. The image's border, legend and annotations must not be interpreted as science pixels. Display changes and image downloads do not alter the numeric GeoTIFF, quality masks, saved scientific results or processing options.

Previously saved results can export whichever layers are still present. The map-image endpoint validates the run, tool and registered layer; callers cannot supply arbitrary file paths. Custom limits, palettes and category-colour overrides follow the same validated preview path. The local download has no external renderer, new service or NASA login requirement once a valid result is saved.

## Verification

The earlier map-image export verification passed **200 Python tests and 71 frontend tests**. Those checks covered:

- An annotated PNG export for each of the 10 tool identifiers, plus an end-to-end export from the actual saved output of every processor using synthetic NISAR-format HDF5 inputs.
- Preservation of applied custom endpoints, P04 Rainbow selection, source context, metadata and automatic reference-outline removal.
- Meaningful binary/water-state/patch-ID keys and observation-index/date correspondence.
- Invalid ranges, palettes, missing results/layers and unrecognized identifiers.
- Hash equality of numeric GeoTIFFs before and after export.
- Complete seven-tool guides, grouped catalogue counts, question/input search, product filtering, P04 rate-versus-pair explanations and download links following the displayed settings.

Continuous and classified outputs were also visually inspected using explicitly synthetic fixtures:

- [Synthetic P04 map layout](validation/tools-ux/synthetic_p05_map.png)
- [Synthetic water-state map layout](validation/tools-ux/synthetic_water_state_map.png)

These images are engineering examples, not observations of Earth or new scientific validation. A fresh browser visual inspection was unavailable in this session. No original or saved area data were deleted as part of the update. Regional validation remains an ongoing study task for each processor.


## P05 earthquake experience · 0.4.2

P05 opens on centimeter displacement with shared Rainbow/Diverging palettes and Custom numeric limits. Its guided setup supplies the approximate Venezuela publication region and documented event time on explicit selection. A P05-only event-coverage selector adds adjacent same-direction/release frames; separate source dates, references, overlap differences and all original maps remain visible and downloadable. Overlap differences are summarized in the reliability explanation rather than treated as independent accuracy. See [the real Venezuela comparison](P05_VENEZUELA.md) for the three usable frames, the rejected source and the remaining scientific differences from the published illustration. The current suite passes 228 Python and 96 frontend tests.


## Shared controls and corrected phase screening · 0.4.3

All seven tools use the same palette registry (Default, Diverging, Rainbow) and range controls (automatic shared, automatic per-map, full and custom). Class/ID/date maps show labelled editable category swatches, with numerical range controls hidden. Custom category colours follow the preview into its PNG and can be saved with the opening view; reset applies to that classification across its dates. Unavailable maps show an explanation and hide irrelevant controls. P04/P05 default to the same Rainbow lookup. Geographical names are no longer display-setting labels. Shared GUNW input screening decodes delivered packed validity masks before averaging. P05 mosaics prefer shared reference cells, with explicit independent-reference fallback. The real-data investigation and revised comparison are in [P05_OVERLAP_REVIEW.md](P05_OVERLAP_REVIEW.md). Verification passes 232 Python and 97 frontend tests.

## Shared reference preparation · 0.4.4

All three reference-based tools now have the same **Find or check a reference** action. The assessment panel uses product-appropriate units, source-order explanations, current-reference warnings and explicit candidate adoption. Phase coherence and annual rates are absent from GCOV cards; annual rates are absent from P05 cards. Saved assessment restoration returns to the correct tool, product, event coverage and baseline. Candidate provenance cannot travel silently between tools. See [the reference assistant guide](REFERENCE_ASSISTANT.md).

### PNG area and download controls

**Download GeoTIFF** and **Download PNG** are styled download buttons. **PNG area** affects the image only; the GeoTIFF keeps the complete saved numerical grid. **Include background** uses the selected basemap and the main map’s Place names state. Current-view PNGs preserve the camera’s geographic bounds/aspect ratio within the standard report layout; they are not browser screenshots. Panning/zooming updates the PNG request, and download captures the latest camera. Legends and range are never recalculated from the crop. The automatic blue reference outline is omitted, while the saved processing reference and its effect on values remain unchanged. The reference-support diagnostic itself is still available as an explicitly selected quality map.

### One download location beside the map

**Download this map** sits immediately below the map colour scale and names the active layer. PNG area, Include background, PNG and GeoTIFF buttons and the run-record JSON link are grouped here. Changing the result or date updates the same controls; no duplicate numeric download action remains under the result chart. All grouped result views route selected layers to this panel; there is no separate flat catalogue. An unavailable layer shows the reason here, hides the PNG action and retains its saved numeric file, which can contain no-data values. New exploration hides the entire result/download panel with the old result.
