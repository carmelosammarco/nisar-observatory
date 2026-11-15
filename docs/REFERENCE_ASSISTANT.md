# Choose a reference before processing

The same assistant is available from **Set up inputs → Find or check a reference** in all five tools that use a spatial reference. Draw your study area and select the observations first. A reference is an area within the study rectangle whose measurements define the spatial origin of the result; it is not an extra satellite product.

| Tool | Reference assumption | Assistant comparison |
|---|---|---|
| P03 · After Fire Observatory | Comparable, unaffected scattering, justified independently | Per-observation reference departures from the declared median baseline, in dB |
| P04 · Sinking City Atlas | Stationary ground relative to the interpreted motion | Per-pair LOS offsets in cm; annualized reference-rate sensitivity if a connected record supports it |
| P05 · Quake Evidence Explorer | Ground outside the suspected rupture/deformation, independently justified | Event-pair LOS offsets in cm, separately for each source view; never an earthquake annual rate |

## A simple sequence

1. Select compatible source files, including local subsets. P05 additionally needs the documented event time; adjacent views require explicit event coverage mode.
2. Open the assistant. It assesses a reference you already drew, if any, and proposes up to three separated patches. Saved inputs use the same reader and product-specific grid as the actual processor. An unreadable selected source stops the assessment.
3. Inspect **shared coverage**, **spatial variation** and, for phase products, **worst-pair median coherence**. Use **Locate on map** to check the setting and avoid suspected change. Supplied affected polygons are excluded from suggestions.
4. Read each warning and the offsets relative to Candidate 1. Offset entries follow the displayed source/date/group order. Switching reference subtracts those offsets from the corresponding maps. Candidate 1 is zero by definition.
5. Choose a patch explicitly or draw your own; processing does not start automatically. **Run with this reference** still checks the tool's other required inputs. A candidate rectangle can replace existing reference polygons only through the explicitly labeled action, with an undo option.
6. Inspect the actual reference-support and quality maps after processing. The selected assessment is retained in the result, alongside exports and source provenance.

## What the checks establish

At least **25 shared analysis cells** and **80% usable patch coverage** are needed for a suggestion. Up to 225 windows are assessed at up to three sizes, down to 6 × 6 cells, so narrow overlap strips are not missed by one large window. Integral coverage scans identify windows before exact assessment. Candidates are separated spatially. The search is bounded; it is not an exhaustive optimum over all possible areas.

GUNW ranking uses worst-pair median accepted-sample coherence, shared fraction and within-patch phase MAD. Median coherence below **0.70** remains flagged **review needed**; it does not silently discard every usable but imperfect alternative. GCOV ranking uses shared positive-power coverage and spatial dB uniformity; no phase coherence is invented. Low spatial variation does not establish small temporal change.

These are engineering screens, not calibrated confidence thresholds. High coherence means consistent echoes; coherent ground may move. A uniform brightness patch may have changed everywhere. No automatic DEM, elevation, vegetation, stable-ground or unaffected-ground classification is made. Independently sourced context remains necessary for those assumptions.

P05 event mosaics prefer the same reference cells across every selected source. The assistant evaluates that shared support. The actual processor explicitly reports independent group references if fewer than 25 physical cells can be shared; it does not label such a mosaic as commonly referenced. For mosaic comparison-ground checks, support is the union of each group's comparable coverage, rather than requiring all groups to see the whole region.

Changing the tool, area, files, quality/correction settings, event selection, baseline or domain/affected polygons invalidates candidate adoption. Reference polygons take precedence over rectangles. Old assessments remain readable, but changes to the assistant/reader require a fresh assessment for adoption. No candidates or thresholds are silently applied.

## Venezuela data review

The saved three-source Venezuela subsets have only 979 analysis cells in common, all inside the broad former reference. That rectangle contains 109,824 grid cells: only **0.89%** support is shared, and its worst-view median coherence is **0.452**. A large blue box therefore substantially overstates the usable reference footprint.

The multiple-size search identifies smaller patches with 31–34 shared cells and **86–94%** shared coverage. Their worst-view median coherence is **0.478–0.555**, so all remain **review needed**. The largest per-view offset spread between these three candidate choices is approximately **2.15 cm**. This is reference-choice sensitivity, not a displacement accuracy bound or proof of stable terrain. The fourth downloaded source previously failed coherent-component screening and is not silently reintroduced.

See the saved [assessment](validation/p06-overlap/shared-assistant.json), [overlap investigation](../Examples/P05_Venezuela/references/p05_OVERLAP_REVIEW.md), and the new end-to-end verification record in `validation/shared-reference/`. These engineering checks do not reproduce an independent geodetic validation of NASA's map.

### End-to-end P05 comparison

Both tests use the same three native subset sources, delivered quality masks, ionosphere subtraction, event time and analysis grid. Independent recalculation matches every group's saved phase-to-cm values within **0.000016 cm**, and the source-choice mosaic and reference masks agree cell for cell. No remote science bytes were read.

| Reference tested | Shared reference cells | Median overlapping-view difference | 90th percentile difference |
|---|---:|---:|---:|
| Existing broad reference | 979 | 0.49 cm | 4.62 cm |
| Assistant Candidate 1 | 31 | 0.87 cm | 4.82 cm |

The smaller patch has better box coverage and coherence but slightly worse overlap agreement. **The assistant does not automatically replace the existing reference, and does not optimize away disagreement by fitting the earthquake signal.** The broad reference remains a useful comparison. Physical stability, correlated errors and viewing-geometry differences need independent investigation; neither overlap metric proves which reference is correct.

The assessment and both result runs are saved in **Your runs**. [Verification record](validation/shared-reference/verification.json) · [Candidate-reference map with scale](validation/shared-reference/venezuela_assisted_reference.png). The new assistant and existing P05 processing were checked numerically and through the local API; a new interactive browser acceptance check was not performed.

### When a selected file blocks the check · 0.4.5

A catalog footprint or saved HDF5 file does not guarantee usable science pixels. The Venezuela track 061, ascending frame 006, June 18–30 subset has no coherent connected-component pixels surviving the current quality screen. Including it blocks the P05 calculation and the reference check. Changing the reference does not repair that input.

Both failed P05 results and failed reference checks identify this quality failure and offer **Deselect unusable file(s) & find a reference**. This explicit action changes only the current analysis selection and reruns the assistant on the remaining files. No input is deleted, no threshold is reduced, and authentication/schema errors are not offered as quality exclusions. Changed workspaces cannot apply an old exclusion action. The final reference still requires **Use this reference** followed by processing.

The frontend now compares timestamps by their actual instant, preserving sub-millisecond distinctions. Equivalent ISO timestamps such as `.053Z` and `.053000Z`, or equivalent UTC offsets, no longer make an assessment appear stale after the server normalizes its timestamp.

Renaming or moving a complete subset folder within `data/subsets/` is now supported: the reader locates the original HDF5 filename beside its matching subset sidecar when the stored download path no longer exists. It leaves your folders and metadata untouched, and rejects paths or symlinks outside the subset tree. Keep each HDF5 file and its sidecar together, or use the application's HDF5 import action.

The reproduced user selection also had zero valid cells shared across the three usable views inside its manually drawn reference. After the explicit quality exclusion, the assistant returned three candidates and an adopted 31-cell reference produced a completed P05 run with zero remote science bytes. See [recovery verification](validation/reference-recovery/verification.json). All 247 Python and 105 frontend tests pass; verification included live API processing, without a new interactive browser acceptance check.

## Assistant 2.1 · shared optimization review

Search is stratified across the full study grid, with up to 72 spatial seeds and three global quality seeds per size (up to 225 exact assessments over three sizes). Earlier equal-coverage ties could exhaust the search near the northern edge. Phase candidates first prefer median coherence at least 0.70, then at least 100 shared cells when available; smaller patches remain possible with a warning and the 25-cell minimum. GCOV also prefers larger support without inventing phase coherence. Neither ranking certifies stable or unaffected ground. Old assessments remain readable, but candidate adoption requires a fresh 2.1 assessment.

See [the current processing guide](PROCESSING.md) and [Mexico City tutorial](../Examples/P04_Mexico_City/README.md) for the shared reference method and its limitations.
