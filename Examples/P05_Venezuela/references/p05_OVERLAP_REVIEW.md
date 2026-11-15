# P05 overlap investigation · application 0.4.3

The large differences were not explained by viewing geometry alone. A missing validity check admitted invalid source samples, and the mosaic used different reference origins. Both are now corrected without fitting earthquake pixels to a published picture.

## What was found

| Finding | Evidence | Change |
|---|---|---|
| Delivered validity mask was ignored | Native samples with zero phase, coherence above 0.30 and component label 1 nevertheless had an invalid reference/secondary subswath in the delivered mask. | Decode the paired valid-sample mask **before native averaging**, then apply coherence/component screening. |
| Packed mask needs exact integers | The source mask is uint32; its low byte encodes subswaths, while upper bits carry anomalies and ionosphere-interpolation provenance. Float32 cannot represent every uint32 value. | Read packed masks losslessly through float64, decode uint32, reject missing/fill/invalid subswaths and anomaly flags. Do not reject valid zero phase by value. |
| Different reference terrain shifted the views | The broad rectangle supplied different reference cells to each group. Raw phase origins are arbitrary and cannot be compared directly between files. | Prefer **979 identical valid analysis cells** shared across all selected groups inside the original reference rectangle. No event-pixel offsets, ramps or overlap fitting were used. |
| Corrections and geometry still matter | Intervals and LOS vectors differ; the delivered ionosphere estimate can be interpolated, and other atmospheric/tidal corrections are not implemented automatically. | Preserve correction provenance and interpolation-fraction maps; retain per-group and overlap diagnostics. |

The valid-sample decoding is shared by all GUNW tools: P04, P05, P08 and REMOVED_FROZEN. Existing saved outputs remain unchanged. Native reader **0.3.1** uses a new cache key, so old arrays are not silently reused for new runs. Mask absence is explicitly reported; an unknown delivered encoding stops with an adapter message.

A mask's water flag is not automatically treated as missing displacement. Bit 24 describes interpolated ionospheric estimates and is preserved as quality evidence rather than rejecting almost all interpolated values. Native masks and their encoding are recorded in source attributes.

## Real-data comparison

Same three retained NASA native extracts, same dates, same requested area, same coherence threshold, same delivered ionosphere subtraction, same original reference bounds, and the same 284.1 m analysis grid. No new science download was needed.

| Calculation | Median overlap difference | 90th percentile |
|---|---:|---:|
| Previous processing | 2.65 cm | 40.31 cm |
| Delivered mask applied; independent references retained | 2.15 cm | 12.08 cm |
| Delivered mask plus identical reference cells | **0.49 cm** | **4.62 cm** |
| Previous processing, restricted to cells also in revised overlap | 2.41 cm | 12.09 cm |
| Revised processing on that same cell intersection | **0.49 cm** | **4.62 cm** |

Overlap support changes from 32,815 to 27,643 cells because invalid contributors are removed. The same-cell comparison separates that support change from improved referencing. These differences measure internal agreement, **not independent displacement accuracy**.

The original numerical run was no longer present during verification. Its before-state was reconstructed from retained **reader-0.3.0 real input arrays**, using the original independent-reference calculation and source-selection rule. Its median and p90 exactly match the retained earlier verification record. Those old arrays were used only for the before comparison; the revised run uses reader 0.3.1. The original annotated image is retained separately.

The new study is **c6dc32cf7ce747a19b7e95586f1fb1e8**, in Your runs. Independent recomputation confirms the phase-to-cm conversion, identical reference masks and selected source at every mapped cell. See [verification](../../../docs/validation/p06-overlap/verification.json) and the current [protected-recipe verification script](../../../scripts/check_example_inputs.py).

## Reference sensitivity

The original rectangle was retained; it was not tuned to the NASA picture. Two smaller inland rectangles were also tested:

| Reference | Shared cells | Overlap p90 | Regional median LOS change |
|---|---:|---:|---:|
| Original broad inland rectangle | 979 | 4.62 cm | −2.25 cm |
| Smaller inland rectangle A | 585 | 4.47 cm | −2.46 cm |
| Smaller inland rectangle B | 340 | 5.36 cm | −2.12 cm |

These choices give broadly consistent internal results, but do not prove stable ground. The reference still needs independent geological/geodetic justification. See [exact sensitivity inputs and results](../../../docs/validation/p06-overlap/reference-sensitivity.json).

If fewer than 25 reference cells are shared across all selected inputs, P05 explicitly retains independent group references and warns about origin differences. This is an engineering support threshold, not a scientific accuracy threshold. The tool never fits away an earthquake signal to make adjacent images look smooth.

## Compare with NASA again

[NASA's published illustration](https://science.nasa.gov/earth/earth-observatory/where-venezuelas-earthquakes-shifted-the-ground/) and the revised map show a positive western coastal transition and a negative band along the coast toward Caracas/La Guaira. The conspicuous narrow stripes and source-gap artifacts in the earlier app map are removed. Both app comparison images use the **same −50 to +50 cm endpoints**, making the visual comparison meaningful.

The revised result is closer **qualitatively**, but local amplitudes and coverage still differ. Approximate La Guaira-box values remain more negative than NASA's cited local geological value; these are different spatial summaries and potentially different LOS/processing/reference quantities. Do not claim an exact amplitude match. Production versus original Urgent Response processing, atmospheric corrections, reference stability, remaining unwrapping errors, differing post-event dates and LOS vectors remain possible contributors. A numerical NASA raster and documented processing/reference choices would be needed for a pixel-level validation.

Earlier map:

[Current published-reference and app-result figures](../README.md#visual-comparison). Historical development figure omitted; the report text below retains the earlier experiment.

Revised map with **Diverging**:

[Current published-reference and app-result figures](../README.md#visual-comparison). Historical development figure omitted; the report text below retains the earlier experiment.

Revised map with **Rainbow**, using identical numeric values and limits:

[Current published-reference and app-result figures](../README.md#visual-comparison). Historical development figure omitted; the report text below retains the earlier experiment.

## Shared settings

All fourteen tools use one shared display-control definition:

| Setting | Choices | Meaning |
|---|---|---|
| Palette | **Default**, **Diverging**, **Rainbow** | Reusable numeric color schemes. Class/ID maps keep fixed semantic colors. |
| Range | **Automatic · shared across dates**, **Automatic · this map**, **Full range**, **Custom** | Custom supplies fixed limits in the active layer's units; for the NASA comparison enter −50 and +50 cm. |
| Units | Shown with every map and range | P04's annual/monthly conversion remains available for rates. Displacement remains in cm. |

The previous P05-specific palette had been chosen to resemble NASA's publication: blue–white–yellow–red. It was not the full Rainbow lookup. **Rainbow now uses the same 256-color lookup in P05 and P04**, including cyan, green and yellow. P04 and P05 default to Rainbow; Default and Diverging remain available. A symmetric Rainbow scale has green near zero, while Diverging has a light center. Read the numeric legend; palette changes do not change measured values.

Geographical/tool names were removed from visible display-setting names. Old API identifiers remain supported for existing links, but are not separate user-facing settings. Common phase validity checks are also reused rather than implemented separately for P05.

## Verification and sources

- **232 Python tests and 97 frontend tests** pass, including native packed-mask precision, valid zero-phase retention, shared-reference support, historical fallback, generic palettes in another product, and shared controls across all fourteen tools.
- Independent checks use local genuine NASA extracts, not simulated surface measurements.
- Revised annotated map images were visually inspected. Representative preview/GeoTIFF/PNG API paths were checked. No new interactive browser acceptance is claimed.
- [Official GUNW guide](https://nisar-docs.asf.alaska.edu/gunw/) explains the delivered correction layers and their default application status. Mask decoding follows the exact encoding description embedded in the downloaded HDF5 files.
- [ISCE3 mask issue](https://github.com/isce-framework/isce3/issues/224) provides additional context on why geocoding fill and invalid radar support require care; it does not itself diagnose this app's bug.
