# Browser acceptance · shared P05/P06 flow · 0.4.8

The check uses the existing Chrome app tab and real native HDF5 area extracts. The local data and saved runs had been cleared before this check. Recovery retrieves subsets only; no complete originals are downloaded. Earlier full-original comparison receipts remain in `../mexico-replay/`.

## Changes prompted by browser inspection

- Results show the same three-stage progress strip, with Explore results active.
- Your runs labels distinguish saved extracts, reference checks and tool results.
- The checklist describes the assistant path without making a pre-drawn reference a prerequisite. The duplicate setup action is removed.
- Reference Locate provides a direct Return to reference choices action. Choosing a reference brings its Run action into view and uses the full tool name.
- Prepare explains an active job before submitting more work.
- P06 offers one active event-timing input: exact time or date only. Switching modes clears the unused value on Continue.
- Entering Explore refreshes the saved-file inventory, removes missing saved inputs from selection and clears stale local availability flags.
- Save this as the opening view stores the displayed map, unit, palette and applied range with a saved result. Unapplied custom changes must be applied first. The save action is disabled while a preview is loading.
- The server validates the saved layer and unit, atomically changes display metadata and leaves processing inputs and numerical rasters intact.

## Automated checks

Python: 283 passed. Frontend: 131 passed. Logs are saved alongside this file. One existing Starlette/httpx deprecation warning remains.

## Browser outcome

Both workflows completed in Chrome using real local subsets. P05 browser run **f58acf04** restored all six exact comparison sources and the original reference, with 510,464 common cells and 2,698 reference cells. Its summary values and numeric rate raster match the restored baseline. A temporary −24…+24 cm/year opening range survived reopening, then the original **Rainbow −30…+30 cm/year** was saved again. Switching to cm/month now updates both the map and visible inputs to **−2.5…+2.5**. Reopening after P06 and a service restart restores the saved annual view.

P06 browser run **76126bac** uses three real views after an explicit exclusion of the unusable fourth view. New exploration's starting coherence 0.40 produced no candidate. The check exercised the visible Review data & shared settings recovery and explicitly applied the shared phase recommendation (coherence 0.30 and delivered ionosphere subtraction). Candidate 1 has 34 shared cells and a worst-pair median coherence below 0.70; review warnings remain visible. These tests do not establish physical stability. Locate/Return, candidate choice, processing, Next and Play worked; playback reached the final source interval. The saved main map reopened with Rainbow and automatic shared scaling.

The live receipt is in [live-browser-checks.json](live-browser-checks.json). Screenshots document the actual rendered interface, not mockups: [P05 map](p05-result.jpg), [P05 preparation](p05-prepare.jpg), [P06 map](p06-result.jpg), [P06 candidate location](p06-reference-map.jpg), [P06 date-only mode](p06-date-only.jpg).

The first Mexico batch saved five extracts and reported one file-save failure. Retrying that source completed successfully. Completed receipts preserve this history; no source was silently dropped. Six Mexico subsets total 63,022,520 bytes. The four Venezuela subsets total about 166.9 MB. No complete originals were downloaded in this check.

## Additional clarity fixes

The browser exposed a visible P05 unit-conversion bug: internal limits changed, but the editable boxes retained annual numbers. The boxes now update with the unit conversion, including rollback after a failed preview. The assistant distinguishes patch eligibility (25 cells, 80% shared support) from its 0.70 coherence ranking preference. Low-coherence candidates can be offered with warnings. Candidate preview labels are removed when a reference is adopted or a result opens. Saved-extract extent percentages are explicitly distinguished from valid measurement coverage. The sidebar now identifies its input checklist as preparation for a new analysis when a saved result is being viewed.
