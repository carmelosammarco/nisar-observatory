# Reproducible NISAR examples

Release 0.9.0 adds a question-led story and **Explore the recorded result** to every tutorial. The recorded view is explicitly previously computed and read-only; **Run it yourself** creates a separate saved analysis. Acquired-state comparisons, controlled experiments and printable offline reports are explained in the [study guide](../docs/STUDY_GUIDE.md). The seven `recorded/` folders add about 324 MiB of protected computed outputs alongside the 31 HDF5 inputs.

Open **Examples** in NISAR Observatory, choose a card, read its tutorial and click **Start example analysis**. A complete example automatically loads its exact area, local input selection, settings, spatial context, reference window where required and saved display recipe. Opening a tutorial never starts processing.

| Tutorial | Tool and product | Protected subsets | HDF5 storage |
|---|---|---:|---:|
| [Chókwè flood, Mozambique](P01_Mozambique/README.md) | Flood Memory · GCOV | 2 | 118.06 MiB |
| [Wheeler Marsh, Connecticut](P02_Wheeler_Marsh/README.md) | Wetland Pulse · GCOV | 6 | 16.09 MiB |
| [Timber Fire, California](P03_Timber_Fire/README.md) | After Fire Observatory · GCOV | 8 | 488.65 MiB |
| [Mexico City, Mexico](P04_Mexico_City/README.md) | Sinking City Atlas · GUNW | 6 | 60.10 MiB |
| [Venezuela earthquake sequence](P05_Venezuela/README.md) | Quake Evidence Explorer · GUNW | 3 | 158.76 MiB |
| [Krasheninnikov, Kamchatka](P06_Krasheninnikov/README.md) | Volcano Surface Diary · GCOV | 5 | 259.52 MiB |
| [Samudra Tapu, Himalaya](P07_Samudra_Tapu/README.md) | Glacier Motion Pulse · GOFF | 1 pair | 4.59 MiB |

**31 native-grid area subsets · 1,105.78 MiB.** The four earlier cases retain their recorded offline verification. Timber Fire passed integrated application 0.7.0 replay on 20 October 2026, including exact input checksums, numeric rasters, map image/legend and saved scale. [Verification summary](verification-summary.json).

## Choose a demonstration

Start with **Mozambique** for an intuitive two-date story, then **Timber Fire** for quantitative boundary evidence and **Mexico City** for relative ground motion. This selection reflects available numerical evidence and explanation clarity, not a universal accuracy ranking. Each tutorial now separates what agrees, what differs and what remains unverified. [Seven-case evidence matrix](../docs/EXAMPLE_EVIDENCE_REVIEW.md) · [Demonstration sequence](../docs/DEMONSTRATION.md).

## What each folder contains

```text
case/
  README.md                 Full tutorial, exact dates, settings, interpretation and limits
  example.json              Curated recipe and original NASA source identities
  recorded/                 Read-only computed result, rasters, previews and checksum manifest
  inputs/                   Protected native-area HDF5 files
  input-manifest.json       Exact filenames, sizes, source metadata and SHA-256 checksums
  catalog-receipt.json       Public NASA catalog selection evidence
  download-receipt.json      Area extraction progress, retained files and transfer totals
  verification.json         App replay, numerical checks, raster and display checks
  verification-direct.json  Separate local source/provenance and computation checks
  figures/                  Archived comparisons and the fresh verification result
  references/               Original study reports and the fresh replay receipt
```

The tutorials distinguish published imagery, historical studies using other satellites, independent event evidence and our calculated outputs. Read that distinction before interpreting a visual match as scientific accuracy. P04 and P05 retain the recorded comparison reference windows; their physical stability is not certified by coherent radar measurements.

## Storage protection and reuse

These inputs are outside `data/`. Deleting ordinary runs, clearing the reusable array cache or manually removing ordinary downloads leaves the protected copies intact. The app checks every required source and checksum before enabling an example; it does not substitute other dates or processing revisions. Files can still be changed or removed manually through the operating system. Back up the entire Examples folder.

Complete examples process locally without Earthdata sign-in. Basemap tiles and external references can still require internet. Native HDF5 files are self-contained area extracts, not full official products; the complete input folder can also be imported manually through **Import subset folder**.

For a source-only installation missing these inputs, start the app, sign in through Connection, then run from the application directory:

```bash
.venv/bin/python scripts/prepare_examples.py
```

For a complete portable release, include this folder or use the release helper's `--include-example-inputs` option. Ordinary user data and credentials are excluded from that release. No credentials are stored in the examples.

Timber Fire uses the integrated combined HH/HV method with eight protected inputs and no reference rectangle. Its tutorial compares the actual app output with the verified preprint and official boundary, and distinguishes candidate change from burn severity or recovery.

Krasheninnikov is a qualitative NASA-frame comparison using five protected GCOV dates and an already-erupting June baseline. Its signed-change candidates include seasonal/background effects and are not lava boundaries. The tutorial distinguishes the official reference, our numerical output and acquired brightness.

## Shared map appearance

All seven examples use the same controls as the tools. Measurement maps offer Default, Diverging and Rainbow palettes plus automatic or custom ranges. Category maps offer labelled editable colour swatches (including class codes, patches and observed dates); numeric range controls are hidden. Colours and category opacity stay consistent across the matching dated maps of a classification. Other classifications keep their own styles. Reset restores those shared defaults. Save the opening view to retain edits with the saved run. PNG map downloads include the applied colours and legend; numeric GeoTIFFs remain unchanged.

An unavailable result explains the missing evidence rather than showing a misleading empty scale. In the two-date Mozambique example, recovery needs later acquisitions and is therefore unavailable. Editing display colours does not change the tutorial’s processing settings or reproduce a different classification.

**Category opacity:** each swatch has a 0–100% slider. Set a valid background category (often code 0, such as no open-water candidate) to 0% to reveal the basemap while retaining the detected features. This is different from missing data, which remains transparent and is never converted to zero. Styles are shared across dates of the same classification. Category opacity combines with the overall Radar overlay opacity. PNG exports preserve category opacity against a neutral page (no basemap), while truly missing observations use the checker pattern. Save the opening view to keep colour and opacity edits after reopening. Numeric GeoTIFFs are unchanged.

Samudra Tapu is the seventh protected example. One GOFF subset contains both January acquisitions and delivered viewing cubes. The historical outline and tested horizontal-motion assumption load automatically, with Rainbow 0–140 m/year. It is a qualitative published-map comparison and reproducible conditional estimate, not exact paper reproduction or independent speed validation.

