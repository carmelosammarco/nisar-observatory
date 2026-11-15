# Controlled experiments · release 0.9.0

From a completed or recorded result choose **Make a controlled experiment**. The workspace loads its actual recipe, sources and area, retaining the original as a comparison baseline. Change one parameter, check and run; the original remains intact. Save the variant in My Tools or export its portable JSON.

**Compare with another run** lists scientific-option and declared-step differences. Implicit shared defaults are normalized, so explicitly saving an unchanged default is not presented as a changed calculation. The report still distinguishes a guided internal sequence from an explicit editable sequence. Display settings and recipe names are excluded from science differences.

Comparable saved maps have linked views and identical colour limits. Numeric comparison requires matching observations, area, method, exact grid, units, scope and class meanings. It reads raster windows without resampling. Categories report changed-cell fractions; continuous maps use after minus before. No jointly valid cells is an unavailable comparison, not zero difference. The complete map-difference table remains available under its labelled disclosure. [Study guide](STUDY_GUIDE.md).

---

# Experimental workspace and My tools

Declarative workflow engine 1.1.0 · local, single-user application.

Explore Earth opens in an experimental workspace. No guided tool is selected. **New exploration** returns to an empty generic draft. No processing step is added automatically, including when changing product or returning from a guided template to the custom builder. Saved tools and imported recipes retain their recorded steps. Returning through the Explore Earth sidebar keeps an ordinary experimental draft while leaving guided-tool mode. After an example has prepared a workspace, that sidebar action instead starts a clean exploration: no area or reference, no checked files, default settings and no processing steps. Use the tutorial’s **View prepared workspace** button to inspect its recorded setup deliberately. Saved runs, saved recipes and protected inputs remain available. Selecting a geographic preset in experimental mode changes geography, without silently replacing the processing steps with the associated example method.

## A repeatable experiment

1. Draw an area, or select a preset. Select **GCOV**, **GUNW** or **GOFF** in the workflow builder. One workflow uses one product. Elementary operations normally use one compatible acquisition group. Scientific fire blocks preserve separate per-view baselines before fusion; earthquake blocks can form the explicit event-coverage mosaic. Neither operation averages incompatible raw measurements. For GUNW only, explicit mixed-revision permission may join processing revisions within the same view and release family; different geometry or BETA/provisional release families stay separate.
2. Find NASA observations, choose **Use saved data**, or import local HDF5/subset files. Check the analysis rows you want. A baseline of N observations requires at least N+1 selected observations; other custom workflows can start with one observation/interval. Each run accepts at most 32 files. Repeated versions of the same observation are rejected rather than counted as additional dates.
3. Open **Area & analysis settings** for the product's channel, requested spacing, native quality and relevant phase/offset settings. Native screening occurs before averaging. Elementary workflows use the generic equal-area grid; scientific block plans reuse the corresponding established method grid. The generic grid has product floors of 20 m for GCOV and 80 m for GUNW/GOFF, at most 384 cells per axis; actual spacing can be coarser for a large area. Smaller spacing cannot manufacture source resolution.
4. Choose **Editable ordered steps**, or a **guided template** in Starting point. The empty builder offers **Choose a compatible next step**, grouped by purpose: preparation, date comparison, noise reduction, candidate patterns and summary. Selecting an option shows its purpose, a plain-language example, input/output units and limitations before you choose **Add this step**. Add, remove or move steps using their labelled controls. Finish an elementary workflow with a summary, or a scientific block plan with **Choose the opening result map**. **Check workflow** checks schema, parameters, product, order and selected-source metadata, showing exact dates and resource estimates; it does not read satellite arrays or certify physical meaning.
5. Choose **Run workflow**. Source reads, quality, shared spatial support and reference checks happen now. A failed selected source stops the run; no date or coverage is silently omitted.
6. Read the factual findings and executed-step table. Main results show the summary and, when available, the first-to-last processed difference. Explore time shows the processed observations at their actual acquisition times or pair intervals. Quality maps retain native contribution evidence and observation counts. Advanced maps contain intermediate latest-step outputs and observed baseline maps.
7. Give the recipe a name and description and choose **Save as my tool**. After loading an existing saved tool, **Update my saved tool** replaces that recipe; **Save a new copy** creates a separate tool. Completed runs remain unchanged.

New workflows start with **no steps**, and Run remains disabled until the appropriate final summary or opening-map block and its dependencies are present. Decibels are an optional first conversion for GCOV, not mandatory preparation: linear power can also be summarized or compared. GUNW must first convert phase to referenced LOS; GOFF rates must precede other calculations. A categorical mask offers patch filtering and candidate frequency, not numeric smoothing or a measurement average. New calculations are inserted before an existing final summary. Reordering is allowed, but an invalid sequence is explained and cannot run. A readable process review shows the current output units and the next required action.

For a simple GCOV experiment, deliberately add **Convert radar brightness to decibels → Compare with the first observations → Summarize the selected observations**. This measures radar-scattering change. It does not automatically label a flood, fire, eruption or vegetation change. The sample saved tool “Mozambique · custom-step demonstration” uses the two protected January observations and is an engineering demonstration, not a replacement for the Flood Memory case study.

## Available custom operations

| Operation | Input and calculation | Important interpretation |
|---|---|---|
| Power to decibels | GCOV, first step only: `10 log10(positive calibrated power)` | A dB difference is a power ratio. The chosen delivered channel and radiometric normalization still matter. |
| Phase to relative LOS change | GUNW, first step only: subtract the median over identical common reference cells, then `−wavelength × phase / (4π)` and convert to cm | Positive is toward the satellite; negative is away. Wavelength is read from the source. This is not vertical displacement or proof of reference stability. |
| Displacement to interval rate | GOFF offsets or converted GUNW LOS change divided by each exact pair duration; optional multiplication by 365.25 | Per-day or annualized rates describe each pair interval. They do not accumulate motion across overlapping pairs. GOFF retains the configured offset MAD screen and its diagnostics. |
| Subtract an observed baseline | Per-cell median of the first N chronologically ordered observations, then subtract that baseline from every frame | All N baseline samples must be valid. This is an observed baseline, not a long-term climate normal. Pair intervals are compared as intervals. |
| Smooth without filling gaps | Normalized Gaussian convolution, sigma in metres divided by actual grid spacing | Missing central cells stay missing. Smoothing changes effective support and can blend features. It cannot create native detail. |
| Make a candidate mask | At/above, at/below, or absolute magnitude at/above a threshold in the current units | Output categories 0 and 1 describe a declared candidate condition. They are not calibrated environmental classes or probabilities. |
| Keep connected candidate patches | Four-connected mask components, filtered by physical area in m² | Requires a threshold mask. Background stays valid zero; missing evidence stays missing. Small real features can be excluded. |
| Summarize the observed record | Mean, median, population standard deviation, minimum or maximum on cells valid in every final frame; category masks use observed candidate frequency | Frequency is the fraction of selected usable observations meeting the rule, not a continuous duration or fraction of all days flooded. |

The editable GUNW sequence can also **Reconstruct connected acquisition dates** after referenced LOS conversion, optionally with measurement smoothing. It reuses the connected pair-incidence solver, fixes the first acquisition to zero and keeps pair residuals. Requiring a redundant cycle is optional; a connected tree, including the historical Mexico record, has no independent closure check. **Fit a movement trend** then fits an intercept and linear slope to at least three reconstructed dates, in cm/day or annualized cm/year. It creates a single fitted map; the final Mean/“Keep the fitted map” summary preserves that map, rather than averaging pairs. The timeline keeps the reconstructed dates in cm used by the fit. Compatible post-fit operations alter the final map, not those dated displacements. Disconnected or insufficient networks stop; they do not fall back to a different measurement.

All seven protected examples now offer **Load editable workflow** and **Download workflow JSON**. The workspace restores their exact protected input identities, settings, context and opening view. No processing starts automatically. Each card exposes the implemented operation, assumptions, applicable parameters and remove/reorder controls. Missing dependencies block running; **Undo last step removal** restores the preceding sequence. Editing a card clears a potentially obsolete display scale. The original guided examples remain available.

### Scientific blocks shared by product

| Example | Editable sequence | Important assumptions |
|---|---|---|
| P01 · Mozambique | Water rule → flood comparison → optional patch tracking → opening map | Radar-dark candidates; missing later dates cannot establish flood duration. |
| P02 · Wheeler Marsh | Water rule → observed wetness history → optional patch tracking → opening map | Joint HH/HV sigma-zero or single-channel rule. Occupancy is observed-date frequency, not continuous hydroperiod. |
| P03 · Timber Fire | Per-view HH/HV baseline/change → optional smoothing → robust score → threshold → optional patches → opening map | Baselines and latest dates remain separate by view; scene-normalized score is not burn severity. |
| P04 · Mexico City | Referenced phase-to-LOS → connected dates → trend → final-map summary | Relative LOS, not vertical subsidence; reference quality and graph redundancy matter. |
| P05 · Venezuela | Event-bracketing selection → reference/conversion/coverage mosaic → opening map | Different views retain their dates and reference evidence; no damage attribution. |
| P06 · Krasheninnikov | Observed baseline → optional smoothing → signed change → optional patches → change history → opening map | Brightening/dimming can reflect snow or wetness, not only lava. |
| P07 · Samudra Tapu | Optional screening → optional stable-ground bias → geometry solution → rate units → opening map | Horizontal solution fixes vertical velocity to zero; radar components are available as an alternative. |

**Compound scientific block** identifies coupled operations that must remain coordinated, including radiometric conversion/baselines and reference-aware view mosaics. Each scientific block currently appears once per plan; edit its parameters or save another variant rather than repeating the same block. These typed cards compile to shared tested kernels; they do not execute arbitrary code, and every internal equation is not an independent card. Removing a required stage gives an explanation instead of substituting another method. Removing optional smoothing, physical patch filtering or offset screening genuinely disables the relevant option. All retained method maps and diagnostics remain available; every card does not necessarily create its own raster.

The water rule and patch tracker are shared between the flood and wetland histories. Smoothing, threshold and patch operations share their parameters where their measurement units and scientific position permit. You can switch between horizontal and radar-component GOFF solutions after removing the other solution. **Choose the opening result map** selects an output from the complete method, rather than assuming every internal branch is a single linear array.

Optional **Smooth quality-screened input measurements** changes the inputs before the scientific method. Compatible smoothing, thresholds and patches added after the final scientific calculation act on the selected output map and create a separately labelled **Experimental output**. They retain original maps, dated views and method statistics. Read the additional output statistics for the modified map; the original report cannot describe its new values. Category numbers cannot be smoothed. Signed direction categories cannot be treated as binary patches.

All unchanged recipes and their browser-saved numeric exports passed **251 exact numeric raster comparisons** using the 31 protected real subsets. Six methods also matched their existing statistics and dated series exactly. P04 uses the elementary workflow report schema: its check covers the annualized trend, accumulated change, seven reconstructed dates and network/fit residual maps. This establishes implementation equivalence, not independent scientific accuracy. [Verification receipts](validation/workflows/seven-examples/) · [Portable recipes](../Recipes/README.md).

Invalid unit conversions and category operations are blocked: for example, converting a baseline difference as though it were positive power, smoothing category numbers, running a phase interpretation without referenced LOS conversion, or placing another operation after the summary. Duplicate conversions are rejected. A recipe is a bounded JSON description, never executable user code.

## Adapt the established methods

The seven guided tools and protected Examples remain available. Choose a guided tool and **Customize as my workflow**, or choose a guided starting point and **Edit as ordered steps**. Current shared settings are carried into editable cards without importing another region’s example boundaries or source identities. Legacy relative-reference fire and legacy surface modes remain guided; select the supported combined/evolving mode before converting them to blocks.

For an exact case-study replay, open its tutorial and **Load editable workflow** instead. For a new region, establish new compatible data, dates, quality and spatial context. Product compatibility alone does not make a scientifically meaningful workflow; the editor and backend both enforce dependencies, and processing verifies actual source support.

For GUNW custom steps, draw a justified reference inside the selected area using the map's Reference control. Conversion checks that the same valid reference cells survive every selected pair and that usable comparison ground remains outside them. Saved diagnostics retain the reference count and phase statistics. The custom editor does not certify stable terrain or automatically apply a reference from another region. For the full existing reference assistant, use the guided tool preparation before adapting its setup.

## My tools, import and export

**Tools → My tools** lists named workflows independently of the seven built-in methods.

- **Open saved setup** restores its recorded area, shared options and reference. Matching local sources are selected by exact source identity/name, interval and compatible group. Review the selection: missing sources are not replaced by nearby dates.
- **Use current area** applies the recipe at the current location. It clears the old spatial reference, domain polygons and region-specific grid bounds. Select new compatible inputs and justify a new reference. This is a new experiment, not a replay of the original case.
- **Export JSON** shares a portable recipe. **Import recipe** validates it and opens an editable draft; it does not execute or save it automatically.
- **Delete recipe** removes only the named workflow, keeping satellite files and completed runs.

A recipe contains a schema version, engine version, name, description, product, either ordered steps or an existing method identifier, parameters, optional display settings and source/area requirements. It excludes Earthdata credentials, source download URLs, local filesystem paths and the input HDF5 files. Supported versions are checked explicitly. Recipe content is limited to 256 KiB by server validation. The import control accepts JSON files up to 2 MiB so indentation and other formatting whitespace in an exported recipe do not prevent reopening it. Importing validates the content before loading it; malformed JSON explains how to recover. Satellite inputs must be supplied separately, with the same revisions and geometry for exact replay.

Each completed experimental run also saves `workflow.json` beside its `result.json` and numeric rasters. Both the map download panel and the executed-step explanation provide the recipe download. The result records actual input identities, available checksums, exact area, actual grid, reader versions, engine/method versions and a SHA-256 recipe fingerprint. A run can be reopened from Runs after restart without recalculating it. Saving or editing a recipe never rewrites earlier measurements.

Named recipes live in **`data/workflows/`**, separate from **`data/arrays/`** and **`data/jobs/`**. Clearing the array cache or deleting a run keeps My tools. Include `data/workflows/` in personal backups, or export the recipes. Source-only release packages exclude personal runtime data, including My tools; export and share a recipe explicitly when distributing it.

## Scientific and practical limits

Custom workflows are experiments. A valid step order and completed job do not establish that the process detects a particular surface phenomenon. Thresholds, baselines, reference origin, acquisition geometry, gaps, native quality and processing maturity all affect interpretation. PNG appearance and palettes do not change numeric GeoTIFF values. Independent evidence is required for environmental attribution or accuracy claims.

The first implementation is an ordered single-product pipeline, plus adapters for the existing complete methods. It does not provide arbitrary code execution, branching graphs, cross-product resampling/fusion, full 3D motion, automatic physical attribution or a public multi-user service.

Calculations reuse the application's documented adapters and conventions: [processing methods](PROCESSING.md), [shared settings](GUIDED_ANALYSIS.md), [reference selection](REFERENCE_ASSISTANT.md), [GCOV guide](https://nisar-docs.asf.alaska.edu/gcov/), [GUNW guide](https://nisar-docs.asf.alaska.edu/gunw/) and [GOFF guide](https://nisar-docs.asf.alaska.edu/goff/). These references describe measurements and interpretation constraints; they do not independently validate a newly composed workflow.

Saved tools are also listed in Explore Earth under **Many ways to explore → My Tools** and in **All**. Selecting one restores its saved setup and matches available local inputs without starting a run. New, renamed and deleted recipes update this list immediately. Start one selected guided tool or personal workflow at a time.

For a complete browser-tested build, save and replay with real local inputs, follow [the Mozambique experimental tutorial](WORKFLOW_MOZAMBIQUE.md). It explains why the two-date mean includes a zero baseline and differs from the full change map.


Shared settings identify the current workflow and its inferred scientific method. Source/grid/quality and applicable reference or spatial context remain shared; parameters owned by cards are not repeated in a second form. Empty experimental workspaces explain how to return to Check/Run instead of offering an inapplicable guided-tool preparation button.


Explore Earth presents **Start with the evidence** before **Build a process you can repeat**, keeping data discovery, file selection and download controls ahead of the processing cards for search results, local files and imported examples.

## Workflow checks and result records

Execution engine **1.1.0** accepts older 1.0.0 recipe declarations and records the version actually used. **Check workflow** now checks selected metadata and shows exact baseline/later dates, reference requirements, connected-pair warnings and estimated grid memory without reading or downloading satellite arrays. A valid recipe can still be saved before obtaining its inputs. Run applies the same checks and then verifies native quality and usable support.

Smoothing has one contract throughout: normalized Gaussian, reflected edges, at least 30% finite kernel support, and no filling missing central cells. Compatible map operations may repeat after a scientific method and retain their own settings; compound scientific blocks stay unique. Removing optional water tracking skips its actual computation.

New results include a shared interpretation panel and an execution fingerprint distinct from palette choices. GeoTIFF band metadata includes descriptions, units and explicit category labels. See the [verification guide](VALIDATION.md) for the protected workflow replays and why a changed method needs fresh evaluation.
