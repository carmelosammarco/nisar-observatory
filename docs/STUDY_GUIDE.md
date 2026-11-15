# From a question to a repeatable NISAR study

Release 0.9.0 provides two routes into the same scientific workspace. Start with a documented example to learn how a result was obtained, or investigate your own area to build a new experiment. Neither route automatically assigns a physical cause to radar change.

## 1. Choose a starting point

| Your aim | Start here | What happens |
|---|---|---|
| Understand a real case quickly | Explore Earth → Explore a documented example | Seven tutorials separate the question, observations, interpretation and external evidence. |
| Inspect an existing result immediately | Tutorial → Explore the recorded result | Opens protected, previously computed maps. No job, download or Earthdata login is started. |
| Repeat the documented calculation | Tutorial → Run it yourself → Start example analysis | Loads the exact protected sources, area, settings and scale, then creates your own saved run. |
| Change the calculation | Result → Make a controlled experiment | Loads the actual workflow as editable steps and retains the original as a comparison baseline. |
| Investigate another location | Explore Earth → Investigate my own area | Draw an area, find observations, review compatible sources and choose or build a method. |

Begin with **Mozambique** for a two-date water story. Continue with **Timber Fire** for quantitative boundary evidence, then **Mexico City** for relative ground motion. These demonstrate different quantities and evidence strengths; they are not an accuracy ranking.

## 2. Read a result in the right order

1. **What this run found** comes from the saved calculations, not from a general-purpose text generator.
2. Read the observation dates, number of files, map units and valid support. One paired file describes one interval; it is not two independent velocity observations.
3. Inspect Main results, then Explore time and Quality & reliability. Unavailable maps explain which evidence is missing. Missing support is never presented as zero change.
4. Read the physical hypothesis and its alternatives. A matching case receives its case-specific context; arbitrary regions receive generic interpretation guidance.
5. Follow the comparison tutorial and original references. A visual resemblance to a publisher figure is different from a numerical, spatially matched evaluation.

The recorded example banner remains visible. Its appearance can be explored and exported, but its protected opening view cannot be overwritten. Run the example to save your own personalized result in Runs.

## 3. Compare actual acquired observations

Choose **Compare acquired observations**. Select two different states of the same quantity and compatible viewing group. The linked panels share a colour range and map position. The plain background means no mapped observation; valid negative classes are different from missing data.

These are measured snapshots or reconstructed acquired epochs. They do not create daily observations between acquisitions. A single GOFF interval has no independent speed time series to animate or compare. Different viewing groups or quantities are rejected rather than forced onto a misleading common scale.

[See the acquired-state interface](screenshots/scenario-b/acquired-states.png).

Published reference images retain their own extents, dates and legends in the tutorial. They are not silently overlaid or treated as registered reference rasters.

## 4. Make one controlled experiment

Choose **Make a controlled experiment**, read the editable cards, and change one setting. **Check workflow** assesses input compatibility and requirements; **Run workflow** creates a separate result. Save a named recipe in **My Tools** to reuse it, or export its JSON. A recipe stores steps, settings and source identities, not satellite files or credentials.

For an approachable demonstration, use Mozambique and change the water threshold from **−17 dB to −18 dB**. Keep every other setting and input fixed. The documented original finds **90.47 km²** of new water candidates; the stricter threshold experiment finds **51.40 km²**. This measures sensitivity to a rule. It does not prove either classification is correct.

From the new result choose **Compare with another run**. The original is “before”; the open result is “after.” The comparison shows changed scientific options and ordered steps, excluding display styles. It also provides linked matching maps with one common colour scale.

Numeric differences require identical source observations, area, method, raster grid, units, spatial scope and category meanings. Continuous differences use **after minus before**. Categories report the fraction of jointly valid cells whose class changed; class numbers are not physical magnitudes. The support counts matter: a changed mask changes the population being compared. Incompatible or missing maps give a reason instead of an invented score.

## 5. Keep a useful study record

**Download study report** exports a self-contained HTML document containing the currently selected result map and full legend, findings, observation summaries, scientific settings, declared workflow order where present, sources, applicable references, hypotheses and limitations. Apply pending colour-range edits before exporting. It opens without the app or a network connection; print it or save it as PDF in a browser.

The report uses a portable map without external background tiles. Use the normal map PNG controls if you want an allowed basemap and the current map view. Keep the numeric GeoTIFF for GIS work, complete result JSON for provenance and exact recipe JSON for repetition. The report does not embed HDF5 inputs, private filesystem paths or an Earthdata session.

[Open a real exported report](validation/scenario-b/mozambique-study.html) from the −18 dB Mozambique sensitivity experiment, or [preview its layout](screenshots/scenario-b/report.png). This is a saved demonstration result, not a new analysis started by opening the document.

## Storage and release boundaries

Each `Examples/<case>/recorded/` contains read-only numeric maps, previews, result metadata and a checksum manifest. Together the seven records occupy about **324 MiB**, in addition to **31 protected HDF5 subsets** occupying about **1.08 GiB**. Deleting ordinary runs or clearing the runtime array cache does not delete these example files. Manual filesystem changes still can.

The source-only packager includes recorded results and tutorials, while excluding HDF5 inputs unless `--include-example-inputs` is supplied. A source-only recipient can inspect recorded results; rerunning requires restoring the exact protected inputs. Never describe a source-only package as containing runnable satellite examples unless its inputs are included.

This is a trusted **local, single-user research application**. It is not a hosted multi-user service. Reproducible calculations and developer browser checks do not establish independent scientific accuracy, beginner usability or disaster-response suitability. No competition outcome is guaranteed.
