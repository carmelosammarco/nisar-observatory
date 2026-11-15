# Current guided presentation · 0.9.0

Start with **Explore Earth → Explore a documented example → Mozambique**. Read the question, then explicitly choose **Explore the recorded result** and explain that it was computed previously. Compare the two acquired states, inspect the new-water map, and distinguish a radar candidate from verified inundation. Run it yourself when demonstrating live calculation.

For the modular demonstration choose **Make a controlled experiment**, change only the water threshold to −18 dB, run, and compare with the recorded original. The selected footprint changes from 90.47 to 51.40 km² of new-water candidates; this is threshold sensitivity, not accuracy. The comparison uses shared colours, exact matching grids and jointly valid cells. Save in My Tools and download the offline report.

Then use Timber Fire to discuss independent-boundary evidence, and Mexico City for relative LOS motion and its reference. All seven stories remain available. [Study guide](STUDY_GUIDE.md).

**The embedded About video was made before the 0.9.0 guided-study controls.** It remains an introduction to the mission and application, not a continuous recording or exact visual record of this release. It was not regenerated or charged to a media service during this update.

---

# Demonstrate the app through evidence

## Watch the built-in introduction

Open **About → Watch the introduction · 2:53**. The compact player sits beside the creator profile, with the challenge and community cards in a second side-by-side row. The layout stacks on smaller screens. The player has native controls for playback, seeking, volume and fullscreen; it does not autoplay. **Expand video** opens a large dialog in embedded browsers too, with Close and Escape support. It uses the same player and preserves the current position. Leaving About pauses it. English captions are already visible in the movie, with a separate subtitle download and readable transcript. Playback is served locally and needs no Earthdata session or external video platform.

The introduction first tours Explore Earth, shared Area & analysis settings, Tools, Examples, Mission library, Runs, Connection and About. It then explains the two-date Mozambique flood case and closes with a final slide. This is an edited presentation of genuine app captures and real results, with synthetic third-person narration, not a continuous live recording.

Active media are in `frontend/assets/media/`: the final MP4, poster JPEG, SRT and transcript. Keep this folder with the app; source releases include it. The final movie hash is `e6aa7ede24bdaecb0a9f0d407a7988d8c08f3f8fa84ae4367ba99cb62e21fd7f`.

NASA SVS [visualization 5661](https://svs.gsfc.nasa.gov/5661/) is the published flood reference. The fresh app analysis reproduced 90.47 km² of new water candidates on 593.92 km² of common usable ground. Different extents and classification meanings allow qualitative comparison only; the map does not measure depth, damage or recovery. Scientific attribution is retained in the images and local media notes.

## A longer live walkthrough

Use protected local inputs for a dependable presentation. A tutorial prepares data/settings but never starts automatically; explicitly choose **Start example analysis**. A previously saved result may be opened for timing, but say that it was computed earlier. Basemap tiles/references may need internet even when processing is local.

## Quantitative evidence · Timber Fire

**Question:** can radar show a real surface change when cloud or smoke complicates optical viewing?

Open the Timber tutorial, show its eight protected observations and fixed pre-fire baselines, then run. Start with the combined HH/HV score and candidate patches. Explain **7,453 ha of candidate radar change**. Show the official perimeter comparison: precision about 0.9965, recall about 0.7244, F1 about 0.8389, on its stated evaluation support. These numbers describe an operational perimeter proxy in one case, not globally accurate burned pixels.

Distinguish the author-output IoU from independent evidence: both radar outputs use the same observations. Point out the absent terrain mask and the preprint status. The opening palette is Diverging with an automatic range; the user-supplied figure is Rainbow. Switch palettes only to illustrate presentation, not improved detection. No burn severity or ecological recovery is measured.

## Start here · make the change intuitive with Mozambique

Show 5 and 17 January, then the new-water candidate map. The recorded **90.47 km²** belongs to this selected footprint and threshold. Use the two NASA images to explain the expanding floodplain, while respecting their wider perspective. Show threshold sensitivity: the candidate area changes substantially. No later date means recovery is unobserved, not that flooding certainly persisted.

## Explore further · a different measurement with Mexico City

Show the connected six GUNW pairs and seven acquired epochs. Read the relative LOS rate and acquired-date reconstruction. Negative means away from the satellite, relative to the recorded reference. Explain monthly versus annual rate units and the 84-day record. NASA supplies a visual comparison, not our numerical accuracy certificate; coherence does not prove reference stability.

## Close with the modular approach

Load one example as editable steps. Explain a step’s input, calculation and output, and show that compatible changes create a new experiment. Save a named variant in My Tools and export its recipe. Reusing a workflow saves effort; a modified workflow or a new region needs new evaluation. The originality is an understandable, reusable route from real NISAR observations to inspectable surface-change evidence.

[Seven-case evidence assessment](EXAMPLE_EVIDENCE_REVIEW.md) · [Tutorials and protected inputs](../Examples/README.md).

## Optional separate rehearsal profile

The maintenance helper `scripts/prepare_demo.py` can prepare fresh saved results from protected local inputs in a **new** directory. For example, from the project root run `.venv/bin/python -B scripts/prepare_demo.py --runtime /absolute/path/to/a-new-demo-profile`. Existing directories are not overwritten. Use a separate free port if you open this profile; do not share the normal app’s runtime folder between servers. A fresh profile is optional and is not required by the About video.

Independent beginner task sessions remain future work. Developer walkthroughs and an edited video are not independent participant evidence. Earlier validation working material was moved outside the app by its owner; no runtime or tutorial depends on it.
