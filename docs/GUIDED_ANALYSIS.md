# Guided discovery · release 0.9.0

Explore Earth offers **Explore a documented example** and **Investigate my own area**. Tutorials now begin with a question, observation context, plausible driver, alternative explanations and confirmation needs. **Explore the recorded result** opens protected previously computed maps without starting a job; **Run it yourself** leads to a new saved analysis. Recorded results are labelled and read-only.

Every result has a concise measured summary, controlled-experiment entry point, compatible acquired-state comparison and offline study-report export. Case-specific explanations are used only when the actual source identities and area match; a different region receives generic measurement guidance. Display styles do not alter numeric values. [Step-by-step guide](STUDY_GUIDE.md).

---

# Shared analysis preparation and reproducible examples · 0.8.0

The main path is **Prepare data → Choose reference → Explore results**. Tools without a reference use **Review inputs** for the middle step. The seven scientific methods remain separate; preparation and reusable controls are shared.

## Start an analysis

1. Select an area. Find NASA data, use saved files or import your files/folder.
2. Choose a tool and press **Prepare**. Confirm the selected measurements and any required event inputs in one setup panel.
3. Press the single main **Continue** action. For reference tools, this checks the satellite measurements and opens reference choices. You do not need to draw a rectangle first. Other tools proceed to analysis once their inputs pass.
4. On the reference step, choose **Keep this reference** for your checked existing area, or locate and choose a suggested candidate. The next main button runs the analysis. A checked reference describes data support, not independently established stable or unaffected ground.
5. Read the result recipe, maps, observed dates and quality evidence. Exports remain available.

Manual reference drawing, recommended phase settings, revision consent and other specialist options live under **Settings, manual reference and other options**. They remain available without competing with the normal main action. The detailed reference measurements and secondary map/download controls are also grouped separately.

## P05 · wider event coverage is part of preparation

P05 setup includes the documented event time and one coverage choice:

| Choice | What Continue does |
|---|---|
| Wider event coverage · choose matching groups for me | Chooses the shortest strictly event-bracketing pair per matching track/frame, preserving direction, mode and release compatibility, then starts the reference check. |
| Only the files I selected | Keeps your current selected files and group mode, then checks them. |

Choose **Exact time** when documented, or **Date only** when the time is unknown. Only the selected timing input is used, so an old exact timestamp cannot override a new date-only choice.

Wider coverage is the starting choice; no separate **Select event coverage across groups** button is needed. Opposite-direction or different-release data are not silently mixed. Dates and source groups remain traceable in the result.

If a source has no coherent accepted pixels, the check identifies it and requires explicit deselection before continuing. Nothing is deleted and quality thresholds are not lowered. An exclusion you explicitly accepted is remembered for the same area, tool and assessment settings within the workspace, so repeated wider-coverage selection does not put that file back. Changing the relevant settings triggers a fresh check; manually selecting the file overrides the remembered exclusion. New exploration clears these working exclusions.

When **Locate** takes you to the map, use **Return to reference choices** to return directly to the assistant. Choosing a reference brings its Run action into view. The checklist and help text use this same path; a pre-drawn reference is optional.

If no suggested patch passes, **Review data & shared settings** opens the relevant settings directly. New exploration resets processing settings. The shared phase recommendation is 80 m requested spacing, coherence 0.30, accepted fraction 0.50 and delivered ionosphere subtraction; applying it is an explicit choice, not a silent relaxation. Settings changes trigger a fresh source check. Some areas still have no suitable reference, and suggested ground remains independently unverified.

## Keep an existing reference

The assistant evaluates the reference that was supplied when the assessment started. **Keep this reference** is available when it has at least 25 shared cells and leaves comparison ground. Warnings about coverage or coherence remain visible in its details. A coherent patch may move, and an apparently uniform brightness patch may have changed; physical stability or unaffected status still needs your justification.

The server verifies the exact assessed rectangle or reference polygons before accepting this choice. Changing the geometry invalidates it. Reference polygons are preserved when kept; adopting an alternative candidate uses the explicit replacement action. The selected assessment is copied into the result.

## Reuse a result

Open a successful result in **Runs**, then choose **Reuse this setup**. The app restores its exact saved local source selection, area, visible and retained advanced settings, date span, archive family and reference. Missing local inputs are reported before replacing the workspace; no substitute files are chosen.

Choose **Save this as the opening view** below the map colors to retain the displayed map, units and applied range with that saved run. Apply edited custom limits before saving. Reopening from Runs restores that choice, including after a server restart. Edited category colours for the run are saved alongside the opening view. This updates display metadata only; input settings, references, measurements and numeric rasters are unchanged.

The result's opening display recipe, when supplied, is separate from scientific processing: palette, range, layer and units. The Mexico replay saves **Rainbow, −30…+30 cm/year** and therefore opens with that fixed comparison scale. A custom range is applied only to its matching opening layer and unit. Changing to another unit resets incompatible limits; numeric GeoTIFFs are unaffected by colors. Reusing a currently displayed result captures its current display choice where compatible.

## Verification and scope

Automated checks cover the combined P05 coverage/reference action, all three reference tools, non-reference processing, missing event inputs, explicit source exclusions, checked rectangles/polygons, stale geometry and scoped saved display settings. The normal service replay of the original six Mexico files is documented in [the comparison report](MEXICO_ORIGINAL_REPLAY.md). The initial 0.4.7 checks used automated control tests, local API runs and inspected exported figures. Version 0.4.8 adds [interactive Chrome acceptance](validation/browser-workflow/README.md) for P04 and P05, including data selection, reference checks, source exclusions, result viewing, playback, saved scales and reopening after a service restart.

Version 0.4.7 verification: **282 Python tests and 126 frontend tests passed**. The live P05 controller replay started with one selected file, chose four coverage sources, required explicit exclusion of one unusable source, and completed using the remaining three local subsets. Repeating wider selection preserved that explicit exclusion. The six-original P04 replay completed with the original reference and saved Rainbow range. The running service and frontend/library assets responded successfully. Current verification records are available in [the verification summary](VALIDATION.md) and [protected Examples](../Examples/README.md).

Version 0.4.8: **283 Python tests and 131 frontend tests passed**, plus real-data browser runs. The P04 unit switch updates the visible range fields together with the map. Candidate preview labels are removed before result viewing. The saved-result sidebar clearly distinguishes preparation for a new analysis from the result currently displayed.

The dedicated **Area & analysis settings** page always shows shared controls and filters product controls to the selected tool. Earthquake context appears only for P05. Optional correction, sensitivity and diagnostic controls are grouped under **Advanced options**, together with optional spatial context and independent reference data. Changing tools preserves values and does not modify saved results.

## Reproduce a documented case study

Open **Examples** and choose Mozambique (P01), Wheeler Marsh (P02), Timber Fire (P03), Mexico City (P04), Venezuela (P05), Krasheninnikov (P06) or Samudra Tapu (P07). The complete tutorial shows the exact data, settings, reference caveats, comparison figures, published or independent evidence, and limits. Opening a complete example prepares the workspace automatically but never starts a job. **Start example analysis** uses the recorded recipe and creates a new saved run. **View prepared workspace** opens Explore Earth for inspection or custom changes.

The native HDF5 inputs live under `Examples/<case>/inputs/`, outside the disposable `data/` tree. Checksums and all required source identities must pass before Start is enabled. Missing or damaged inputs leave the tutorial available and disable processing; no different scene is silently substituted. Complete examples run without Earthdata login. Normal run deletion and cache clearing keep the protected inputs.

Geographic presets continue to preserve shared controls. For manual work, use the tutorial's settings table or **Reuse this setup** from a saved run. A P04/P05 example loads the recorded reference window without claiming independently established stability; the normal reference assistant remains available for a separate assessment. Case-specific papers and datasets are collected in Examples; Tools retains general methods and product documentation.

## Map controls and examples

The active map legend and **Radar overlay opacity** slider sit directly under the map, above date playback. The larger legend is the single on-screen color key; the result plot has no duplicate miniature bar. Each downloaded map PNG still includes its legend.

Continuous measurements (frequency, brightness or ground motion) allow **Default**, **Diverging** and **Rainbow** palettes and automatic/custom ranges. Water classes, change classes, observed-date codes and patch IDs show an editable labelled colour key. Click a swatch to change its colour; **Reset shared category styles** restores the original colours and opacity across matching dates. Numerical range controls are hidden because category codes are identifiers, not magnitudes. Colour edits affect the displayed map and **Map image + legend · PNG**, while the numeric GeoTIFF and classification stay unchanged. **Save this as the opening view** retains the run’s edited category colours when reopening it. Colour and category-opacity edits automatically apply across matching dated maps, including playback and PNG downloads. The visible scope message shows which dated maps share the style. Identical codes with different meanings (such as water presence versus reference support) stay separate. Large keys show 40 entries initially and offer **Show next**; up to 512 colours per map can be customized.

Opening a saved reference-based result restores its recorded blue reference rectangle, including when the previous workspace concerned another case. Reuse this setup remains the action for preparing a new analysis with the saved processing settings.


## P03 combined HH/HV change · version 0.7.0

New P03 setups default to combined change: at least three pre-fire baseline dates and one post-baseline date **per viewing group**, both HH and HV. No unaffected reference rectangle is used. Each view uses its own median linear-power baseline; absolute HH and HV dB changes are summed, latest valid views averaged, normalized-Gaussian smoothed (80 m sigma), and robustly standardized across the selected land window. Default candidates use z ≥ 2 and four-connected patches ≥ 10 ha. Native support and missing channels are checked explicitly. Local UTM grids are bounded to 2048 cells per side and four million cells.

The previous reference-relative P03 method remains selectable and continues using the shared reference assistant. Earlier P03 sections describe that method. Combined outputs include a dimensionless change score, candidate mask, view count, individual-view dated magnitudes and signed channel diagnostics. A change candidate is not a burn-severity or recovery measurement. Water, terrain and window selection require review; no DEM/LOS shadow mask is applied. See [the exact protected Timber tutorial](../Examples/P03_Timber_Fire/README.md) for tested dates, settings, real-data agreement and limitations.

## P06 surface change

Choose one compatible GCOV viewing group, a suitable observed baseline and at least one later date. New setups offer Evolving change; older recipes retain the previous method. No reference rectangle is required. The same baseline, cell spacing, smoothing and physical patch controls used elsewhere are reused. Start with latest signed dB departure, then latest patches and repeated evidence. Read the acquired brightness sequence separately. A baseline already containing lava cannot recover earlier emplacement; confirm any volcanic interpretation independently. The corrected Krasheninnikov preset keeps mission-wide search dates and supplies the five-date study settings, but does not automatically select those five files from a broader search.

Open **Examples → Krasheninnikov, Kamchatka** for the exact five protected files, recorded June baseline and ±8 dB opening view. The full tutorial retains NASA references, the acquired-brightness sequence, threshold sensitivity and the limits of volcanic attribution. Opening the tutorial prepares inputs; Start remains explicit.

Returning from Area & analysis settings keeps the selected tool and current values. The Explore Earth sidebar starts with no tool selected, as does New exploration. Choose and run one of the seven tools (P01–P07) at a time. River Room and its area preset are not available.

Unavailable maps hide colour controls and show the specific reason when available. For example, flood recovery cannot be evaluated without an acquisition after the comparison date. Transparent or missing values do not mean zero change. Choose another result or add the required compatible observations.

**Category opacity:** each swatch has a 0–100% slider. Set a valid background category (often code 0, such as no open-water candidate) to 0% to reveal the basemap while retaining the detected features. This is different from missing data, which remains transparent and is never converted to zero. Styles are shared across dates of the same classification. Category opacity combines with the overall Radar overlay opacity. PNG exports preserve category opacity against a neutral page (no basemap), while truly missing observations use the checker pattern. Save the opening view to keep colour and opacity edits after reopening. Numeric GeoTIFFs are unchanged.


## Glacier Motion Pulse · delivered layers and rate units

Choose one GOFF viewing group. In Area & analysis settings, select its delivered offset layer, SNR and rate unit. Layer 1 remains the generic default; the Samudra Tapu research preset starts with layer 3 and no spatial outlier filter. The actual correlation-window source samples are saved with new runs. Missing layers stop with an explanation.

Read the latest filtered radar-plane magnitude alongside the signed component, then inspect time, coverage and raw diagnostics. A positive magnitude can contain noise. Components are filtered separately and the norm requires joint valid support; an optional supplied stable-terrain bias is subtracted separately from each component. m/year = m/day × 365.25 and is not horizontal speed or a full year of measurements. Compare filter-off results because global spatial screening can remove glacier flow. The general tool does not declare stable terrain automatically.

For the January 2026 Samudra Tapu investigation, choose the full research preset and the saved January 1–13 ascending pair. The historical glacier outline can be imported as a study domain from [the investigation folder](validation/samudra-tapu/README.md). That report clearly distinguishes the paper figure, real app output and the uncompleted geographic-velocity validation. The accepted [Samudra Tapu example](../Examples/P07_Samudra_Tapu/README.md) automatically loads the exact protected January pair, historical domain, geometry settings and Rainbow range. The area preset is named Samudra Tapu paper's area.

### Optional horizontal glacier speed

In P07 choose **Motion estimate → Horizontal speed**. Both radar offsets and native viewing cubes are required. For older saved subsets, connect Earthdata and press **Prepare geometry for selected GOFF files**; the app creates new copies and keeps earlier files. Then choose the prepared observations on Explore Earth.

Enter a representative ellipsoidal geometry height (5,000 m for the Samudra Tapu investigation). This supplies the height coordinate for native cube interpolation; it does not supply terrain slope. The inversion fixes upward/downward velocity at zero. Flow down a slope, snow matching, noise and residual registration errors can bias the output. No full 3D velocity or surface-parallel DEM correction is claimed.

The main result becomes estimated horizontal speed. Time exploration shows each pair’s own interval; the regional chart compares common valid cells. Radar magnitude and the selected signed component remain supporting diagnostics. East/north velocity and true-north bearing are advanced maps. Quality includes conditioning and a configurable vertical-motion sensitivity scenario; the latter is not an uncertainty confidence interval. Use separate runs for different acquisition groups. See the [geometry comparison](validation/samudra-tapu/geometry/README.md).


## Current shared checks

Guided and editable runs apply metadata readiness before reading science: insufficient baselines, invalid pair dates, disconnected networks, missing references and event-bracketing failures are explained early. The editable **Check workflow** panel also lists exact baseline/later dates and estimated grid memory. Native quality and actual reference support are still checked from measurements. New results start with **How to read this run**, and example cards distinguish comparison evidence from input checksums. See [the refinement record](REFINEMENT_0_8.md).
