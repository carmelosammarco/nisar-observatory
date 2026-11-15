# Guided discovery and experimental laboratory

Implementation target: preserve the seven scientific methods and protected inputs while making the path from a question to a defensible, repeatable result accessible to new users.

Release 0.9.0 adds guided discovery alongside the existing laboratory. [User study guide](STUDY_GUIDE.md) explains the implemented journey. It preserves the product kernels and supplies no new scientific-accuracy claim. A prior computed result is always distinguished from a newly executed analysis.

## Acceptance requirements

- Two clear starting paths: a documented example or a new area.
- All seven examples explain the question, observations, findings, plausible drivers, alternatives, evidence and limitations.
- An explicitly labelled recorded result can be explored before running; running creates an independent saved analysis.
- Comparable acquired states can be inspected side by side with a shared range and explicit dates; no invented intermediate observations or unregistered reference swipe.
- Saved runs expose concise measured findings and retain the existing numeric results and provenance.
- A modified workflow can be compared with its original run, including scientific setting changes and compatible numeric outputs; incompatible comparisons are explained.
- A self-contained HTML study report retains maps, legend, dates, sources, settings and limitations; recipes remain portable JSON without credentials or private paths.
- Guided and editable workflows retain the existing real-data regression results across all seven protected cases.
- README, tutorials, screenshots and source-release guidance describe implemented behaviour.
- Automated regression, real-data integration and browser checks cover the new journeys. Remaining limitations are stated honestly.

No public hosting, Docker, multi-user service or universal scientific-accuracy claim is part of this release.

## Completed acceptance · 1 November 2026

| Requirement | Implemented behaviour | Verification |
|---|---|---|
| Clear starting paths | Documented discovery or own-area laboratory; existing seven tools retained | Real Chrome navigation |
| Seven understandable stories | Questions, actual findings, hypotheses, alternatives, confirmation and one-change exercises | Seven tutorial/result journeys; narrative tests |
| Immediate recorded exploration | Checksummed, read-only records; explicit previously-computed banner; no new job | Seven recorded openings; API write rejection tests |
| Comparable dates | Linked acquired-state maps and common scale; unlike viewing groups and one-interval speed series explained | All seven date-comparison states checked |
| Controlled experiments | Actual editable steps, preserved baseline, shared-scale run maps, option/step differences and bounded raster comparisons | Mozambique −17/−18 dB experiment; 90.47/51.40 km² candidates |
| Accurate opening views | Guided-to-editable annual LOS output name is normalized while retaining Rainbow and ±30 cm/year | Mexico browser replay and every opening-map PNG/range checked |
| Portable study record | Self-contained HTML with map, legend, findings, acquired summaries, steps, settings, source identities and limitations | Browser download/open; HTML escaping and content-policy tests |
| Reproducibility | Seven guided and seven editable runs, all existing reference rasters/previews, saved recipes and restart | 502 exact numeric-map checks; 655 saved previews; 14 runs and seven recipes reopened after restart |
| Preservation | 31 HDF5 inputs, seven recipes and seven manifests unchanged | All 45 pre-update SHA-256 values match |
| Usability and documentation | Linked maps, compact detailed tables, direct numeric edit→Run fix, narrow-screen grid fix, seven tutorials, README and current screenshots | 765 Python tests; 288 frontend tests; seven tabs fit 390 px; no browser page errors |
| Source-release preparation | MIT for original code, separate third-party notices, citation metadata and checksummed source manifest | Packager manifest and maintenance tests; no public publication |

Evidence: [real-browser receipt](validation/scenario-b/browser.json), [numeric verification of those browser runs](validation/scenario-b/verification.json), [independent API/restart gate](validation/scenario-b/release-integration.json), [preservation and test summary](validation/scenario-b/summary.json).

The browser gate uses an isolated temporary profile and the protected local inputs. It does not sign in to Earthdata or download science data. The API/restart check is a separate isolated run. Recorded outputs occupy approximately 324 MiB; they are necessary for immediate read-only study exploration and are not disposable runtime cache.

## Practical limits retained

- Existing external-evidence limitations remain case-specific: qualitative NASA maps, historical wetland method adaptation, operational fire boundaries, LOS reference/geometry assumptions and constrained glacier inversion are not interchangeable accuracy standards.
- Independent novice sessions, screen-reader certification, native Windows/Linux acceptance and larger-workload stress testing remain future work. The narrow-screen check is an automated desktop-Chrome viewport check, not physical-device certification.
- The embedded introduction predates these controls. Its real imagery and explanations remain useful, but it is labelled as an earlier edited tour.
- The existing Starlette/httpx test-client deprecation produces one warning. Tests pass; this does not indicate a failed runtime request.
- Nothing was publicly deployed or submitted. The current release is ready for local research and demonstration within these stated limits.
