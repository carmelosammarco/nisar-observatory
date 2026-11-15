# Verification and evidence

## Browser and release verification

The 0.9.0 checks cover all seven tutorials, their read-only recorded results and replays with the protected inputs. Chrome opens the tutorials, runs both the guided and editable analyses, compares compatible acquired states, saves an edited workflow and exports a study report. The browser receipt also records the seven-tab layout at a 390 px viewport.

| Evidence | What it covers |
|---|---|
| [Browser verification](validation/scenario-b/browser.json) | Recorded openings, seven guided and seven editable runs, Chókwè threshold comparison, saved tools and report export |
| [Numeric replay and saved previews](validation/scenario-b/verification.json) | 502 exact numeric-map comparisons and 655 saved preview checks, including each opening map |
| [API and restart verification](validation/scenario-b/release-integration.json) | 14 saved runs and seven recipes reopened and checked after a restart |
| [Input preservation and regression summary](validation/scenario-b/summary.json) | 31 protected HDF5 inputs, recipe and manifest checksums, and the acceptance test results |

These checks use an isolated local workspace and the bundled inputs. They establish implementation correctness and repeatability for the recorded settings.

## Evidence for each case

| Example | Protected replay | Scientific comparison |
|---|---|---|
| Chókwè | [Receipt](validation/workflows/seven-examples/P01_Mozambique.json) | [Tutorial and qualitative NASA comparison](../Examples/P01_Mozambique/README.md) |
| Wheeler Marsh | [Receipt](validation/workflows/seven-examples/P02_Wheeler_Marsh.json) | [Tutorial and wetland method comparison](../Examples/P02_Wheeler_Marsh/README.md) |
| Timber Fire | [Receipt](validation/workflows/seven-examples/P03_Timber_Fire.json) | [Tutorial and operational perimeter comparison](../Examples/P03_Timber_Fire/README.md) |
| Mexico City | [Receipt](validation/workflows/seven-examples/P04_Mexico_City.json) | [Tutorial and qualitative NASA comparison](../Examples/P04_Mexico_City/README.md) |
| Venezuela | [Receipt](validation/workflows/seven-examples/P05_Venezuela.json) | [Tutorial and coverage/reference sensitivity](../Examples/P05_Venezuela/README.md) |
| Krasheninnikov | [Receipt](validation/workflows/seven-examples/P06_Krasheninnikov.json) | [Tutorial and published radar imagery comparison](../Examples/P06_Krasheninnikov/README.md) |
| Samudra Tapu | [Receipt](validation/workflows/seven-examples/P07_Samudra_Tapu.json) | [Tutorial and constrained glacier-speed comparison](../Examples/P07_Samudra_Tapu/README.md) |

The [seven-case evidence review](EXAMPLE_EVIDENCE_REVIEW.md) explains measurement, coverage and interpretation limits. The [boundary evaluation and replay receipt](validation/example-evidence-review.json) retains the exact Timber Fire counts and geometry provenance.

## Run the checks

From the project root on macOS or Linux, with the pinned environment and protected example inputs installed:

```sh
.venv/bin/python -B -m pytest -p no:cacheprovider -q
node --test tests/frontend/*.test.cjs
.venv/bin/python -B scripts/verify_release.py --output /path/to/api-verification.json
.venv/bin/python -B scripts/verify_scenario_b.py --output /path/to/browser-verification
```

The browser command also needs Node.js, Playwright and Google Chrome. Supply a writable destination for the verification output.

## Scope and limits

Repeatable outputs support the technical checks for these cases. Classification accuracy, causal attribution and reliable transfer to other regions require further independent evidence. The examples explain what their particular references can establish. The verified release covers local use by one person. Native Windows and Linux acceptance, independent beginner sessions and public multi-user operation require separate verification.
