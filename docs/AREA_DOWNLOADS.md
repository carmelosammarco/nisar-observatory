# Save the selected area instead of a complete original

The app offers two separate ways to retain NISAR data locally. Neither changes the original file held by NASA. Both operate on the app’s supported **L-band (LSAR) GCOV, GUNW and GOFF** inputs. Subsetting retains the source instrument and radiometry; it does not convert L-band to S-band. Frequency A/B are subbands within that instrument.

| Choice | Row selection | Saved locally | Best fit |
|---|---|---|---|
| **Save selected area** | Checked **Use in analysis** rows in the current product tab | Native geocoded science/quality windows and bounded scalar/1D metadata, stored as local HDF5 extracts with JSON manifests | Work repeatedly within a selected rectangle without retaining an entire original |
| **Download originals** | Checked **Save original** rows in the current product tab | Complete original NASA HDF5 products | Keep the whole product, all auxiliary data and access to areas outside the current rectangle |

You can also run a tool directly against remote blocks without first saving either kind of file. Processing caches are separate from native saved inputs.

## Simple workflow

1. Draw your analysis rectangle and find compatible NISAR observations.
2. In the relevant product tab, check **Use in analysis** for the source rows you want.
3. Click **Save area from … files**. Read the confirmation dialog, which shows the rectangle and source count before any extraction begins.
4. Confirm **Save selected area**. The progress panel reports source/layer progress and remote bytes read.
5. The completion dialog reports successful extracts, saved size, transfer size, reuse and any individual failures. Completed extracts replace their source rows and remain selected for analysis if you have kept the same area. A partially failed batch retains completed extracts and names the failing sources.
6. Choose a tool, supply its reference or other required inputs and run normally.
7. Later, use **Use saved data** to load saved inputs matching the selected area and dates. A saved area must contain the whole analysis rectangle. Your runs also retains the area-download record; **Load saved rectangle** returns to that extent if you have moved elsewhere.

Existing complete originals are read locally when available; nothing is deleted. The area option deliberately uses analysis-row checkboxes, while the complete-original button uses its own download-row checkboxes. There is no eight-file batch cap on either saving mode. Analysis still has its separate 32-source limit.

## What the extract contains

The extractor reads each source through the existing authenticated, bounded HTTP range reader, or through a retained local original. It does not request a complete file as a fallback.

For GCOV, GUNW and GOFF it retains supported regular geocoded two-dimensional layers under the product's `grids` hierarchy, preserving native values, numeric data types, units and quality flag attributes. This includes compatible polarization layers, phase/coherence/components/correction layers, offset components/SNR, and soil-moisture candidates/quality layers when present. Source coordinate vectors are shortened consistently; bounded scalar and 1D metadata retains CRS, frequency and acquisition context where delivered.

A local extract is **not a complete official NISAR product**. Non-geocoded or multidimensional auxiliary datasets, incompatible grids, cross-file object references and metadata beyond the bounded copy budget are omitted. Omitted dataset paths and reasons are listed in its JSON manifest. HDF5 dimension-reference attributes are not copied; the app uses explicit coordinate datasets. These extracts are intended for this application's supported readers, not promised as general-purpose replacements for a complete NISAR product in every external package.

No analysis threshold, connected-component selection or resampling is applied while saving. Quality screening and analysis-grid averaging occur when a tool runs, so settings can be changed later without re-downloading the same region. The source is recorded as a subset in processing attributes and interpretation notes.

The saved window is a source-projection bounding rectangle with a one-cell reading buffer. It can include pixels just beyond the drawn WGS84 boundary, especially where map projections differ. Analyses use the selected WGS84 rectangle on their usual equal-area grid. The app rejects an analysis extending outside the requested saved rectangle even if a buffer pixel exists there. A reference area must also lie within the analysis rectangle.

## Sizes, limits and reuse

| Quantity | Meaning |
|---|---|
| Geographic area, km² | The drawn rectangle; not a prediction of transfer size |
| Original size | Size of the complete NASA file, before extraction |
| Saved extract size | Actual compressed local HDF5 size, known after saving |
| Transferred bytes | Actual HTTP range blocks read in that operation; includes HDF5 headers and storage chunks and may exceed saved size |
| Reused extracts | Matching source and rectangle were already saved; no repeated source transfer |

Existing covering extracts disable repeated saving in the interface. The server also reuses an exact source/rectangle/version match. **Use saved data** chooses one local entry per source filename, preferring a complete original when one is available, otherwise the smallest covering extract. Partial overlap is insufficient for a saved subset. A normal NASA search continues to represent complete originals; saving an area does not falsely mark the entire original as downloaded.

Limits are 256 MiB of remote ranges per source, 8 million source cells per layer, 512 MiB of uncompressed retained science arrays per extract, and bounded metadata copying (1 MiB per ordinary scalar/1D dataset, 16 MiB cumulative ordinary metadata). Coordinate vectors are retained as required by supported grids. Large regions or heavily chunked files may exceed these limits; choose a smaller rectangle or retain a complete original. Area extraction does not silently downgrade source resolution.

New files live in product/date/time batch folders under `data/subsets/`, outside the web static directory. For example, `data/subsets/GUNW_2026-10-18_21-45-30_UTC/` holds all new GUNW extracts from one download request. Time is UTC; a suffix such as `_02` distinguishes batches started in the same second. Different products get separate folders. Previously saved flat-layout files are retained and discovered alongside the new layout. Each generated HDF5 has a JSON manifest with source identity, rectangle, format version, retained/omitted arrays, content checksum and actual local size. The HDF5 filename retains the original NISAR source name plus a subset suffix; `README.txt` explains reuse. Source identity, original name, product, acquisition dates, saved bounds, version and layer inventory are also embedded inside each new HDF5 file. The checksum is calculated after the HDF5 file is complete. Extracts survive app restarts and run deletion. Back them up with originals and runs if you want to avoid retrieving data again. `data/arrays/` remains a separately rebuildable processing cache.

## Import subsets manually

1. Open the product/date/time folder in your file picker.
2. In Explore Earth choose **Import subset folder** and select the product/date/time folder once. All HDF5 files in the selected folder and its subfolders are imported automatically; JSON, README and hidden files are skipped.
3. Follow the progress count and completion summary. Failed files are listed individually while successful imports are retained. Alternatively, use **Import .h5 data** to select individual files; multiple selection is supported. You do not need to select JSON or README files.
4. The app recognizes these as **area extracts**, preserves the original source and bounds, and stores imported copies in product/time folders. If the workspace has no selected area, the first imported extract supplies its rectangle.
5. Use a study rectangle contained by every selected extract, then supply the chosen tool's normal inputs and run. The pre-run guide and backend reject a study rectangle extending outside a saved extract.

A copied or renamed new HDF5 file can be imported by itself because its provenance is embedded. Original NISAR inputs still require valid original filenames; keep them unchanged. Importing identical subset bytes again reuses the existing local entry instead of creating another copy. An imported folder records the current import time; the original extract creation time is retained in metadata when recorded.

Older flat-layout extracts contain source-name, version and rectangle attributes and remain importable. They may lack an embedded archive source identifier; the importer labels that identity as derived from the original filename rather than inventing a NASA catalog identity. Incomplete or conflicting subset metadata is rejected rather than treating a clipped extract as a complete original. Manually changing an HDF5 file's scientific content is outside the app's provenance guarantees.

The file-detail panel and completion dialog show where data were saved. Existing originals, previous subset folders and completed runs are not reorganized or deleted by this change. New batches reuse already saved extracts in their existing locations rather than copying them into a second folder. File paths from metadata are validated within the managed subsets directory.

## Verification and its limits

Engineering checks compare native-area processing with complete synthetic HDF5 inputs for **all four products**, including science values, quality layers, derived auxiliary arrays and radar wavelength. The tests also verify offline processing admission, smaller dimensions with unchanged data types, duplicate reuse, restored inventory, cancellation cleanup, missing coverage, source limits, failure reporting and authorization. An in-memory remote-source fixture exercises the extraction path without saving an original; it is not a live NASA network test.

The complete suite passed **181 Python tests and 67 frontend tests** on 18 October 2026. JavaScript syntax checks also passed. The current local `data/raw/` folder contains no Mexico City originals, so this change has **not** been rechecked against those real files. It makes no new scientific-accuracy claim. A fresh browser visual inspection was unavailable in this session; frontend checks exercise the controls and their selection logic.

## Official access documentation

- [ASF: accessing NISAR data](https://nisar-docs.asf.alaska.edu/access-overview/) — explains remote access and partial reads without retaining a complete HDF5 product.
- [ASF: transform and subset with GDAL](https://nisar-docs.asf.alaska.edu/gdal/) — official examples for extracting layers, spatial windows and alternative projections.
- [ASF: tools and services roadmap](https://hyp3-docs.asf.alaska.edu/nisar-docs/roadmap/) — distinguishes delivered dataset extraction from planned spatial/full-product subsetting. The app's local native extract is separate from NASA Harmony services.

### Product/time folder and manual-import checks

The storage/import update passes **212 Python tests and 74 frontend tests**. Added checks cover same-product batch grouping, same-second folder collisions, recursive inventory, duplicate reuse, legacy flat storage, manual HDF5-only import into a separate isolated installation for all four products, preserved numeric/quality arrays and wavelength, imported-area boundary enforcement, and rejection of invalid paths or conflicting/missing subset metadata. These are synthetic engineering checks, not a new regional scientific validation.

### Whole-folder import

The folder picker is a browser directory selection: only files inside the chosen directory tree are considered. It does not let the backend browse arbitrary computer directories. Uploads use the existing HDF5 importer, with duplicate detection and saved-area bounds preserved. The final summary distinguishes files loaded from unique source records, ignored metadata/hidden files and failures. One acquisition group per product remains selected; other imported groups stay available. If the study area or search changed while an import was running, the new workspace is kept and imported files can be loaded through Use saved data. File/folder controls are disabled during an import and reset after completion so the same folder can be selected again. There is no eight-file folder-import cap; processing keeps its own 32-source limit.

**81 frontend checks pass**, including nested-folder filtering, mixed-product batches, automatic first-subset area selection without losing earlier files, partial failures, metadata-only selections, duplicate/group handling and workspace-change protection. The backend scientific/import behavior is unchanged from the 212-test storage/import verification above. No new browser visual inspection was available in this session.

## GOFF viewing geometry

New GOFF area extracts retain the delivered LOS east/north vectors, along-track east/north vectors and incidence-angle cubes over a buffered rectangle and all delivered heights. These are bounded native metadata, not invented geometry. Other omitted multidimensional fields remain listed in provenance. Older subsets remain usable in radar mode; the preparation action creates a new copy with geometry through authenticated NASA range reads. Source offsets and earlier copies are preserved. Portable HDF5 imports retain the geometry and its provenance for offline horizontal processing.
