# Cleanup and embedded introduction · 23 October 2026

Confirmed unused production material and regenerable caches were **moved**, not deleted, into `ToRemove/2026-10-23/`, preserving original paths. The optional review folder can be deleted later without affecting the app, installed About video, normal downloaded data, saved runs, My Tools or seven protected examples.

The final video, poster, English captions and transcript are installed independently in `frontend/assets/media/`. No live application or guide links to an archive dependency. Source releases include the installed video and exclude ToRemove.

Moved **2,063 files**, **817.53 MiB** logical size. Moving them does not free disk space until the review folder is removed manually.

| Original location | Files | Logical size | Reason |
| --- | ---: | ---: | --- |
| `Demonstration` | 1073 | 799.09 MiB | Superseded video-production source, older edits, API attempts and separate rehearsal profile; final app playback assets installed independently. |
| `docs/CLEANUP.md` | 1 | 0.00 MiB | Previous cleanup report, replaced by the current inventory and verification record. |
| `.pytest_cache` | 4 | 0.00 MiB | Regenerable interpreter/test bytecode cache; not application source or scientific input. |
| `.pycache` | 929 | 17.56 MiB | Regenerable interpreter/test bytecode cache; not application source or scientific input. |
| `tests/__pycache__` | 2 | 0.02 MiB | Regenerable interpreter/test bytecode cache; not application source or scientific input. |
| `backend/__pycache__` | 41 | 0.73 MiB | Regenerable interpreter/test bytecode cache; not application source or scientific input. |
| `scripts/__pycache__` | 1 | 0.01 MiB | Regenerable interpreter/test bytecode cache; not application source or scientific input. |
| `Validation/Transfer_2026/scripts/__pycache__` | 1 | 0.01 MiB | Regenerable interpreter/test bytecode cache; not application source or scientific input. |
| `.DS_Store` | 1 | 0.02 MiB | Finder folder-view metadata, not an application asset. |
| `frontend/.DS_Store` | 1 | 0.01 MiB | Finder folder-view metadata, not an application asset. |
| `tests/.DS_Store` | 1 | 0.01 MiB | Finder folder-view metadata, not an application asset. |
| `backend/.DS_Store` | 1 | 0.01 MiB | Finder folder-view metadata, not an application asset. |
| `docs/.DS_Store` | 1 | 0.01 MiB | Finder folder-view metadata, not an application asset. |
| `docs/validation/.DS_Store` | 1 | 0.02 MiB | Finder folder-view metadata, not an application asset. |
| `Validation/.DS_Store` | 1 | 0.01 MiB | Finder folder-view metadata, not an application asset. |

## What was preserved

- `data/`: normal downloaded originals/subsets, array cache, saved runs and personal workflows. No cache was cleared.
- `Examples/`: all seven tutorials, references, figures and 31 protected input files.
- `Recipes/`: reusable current workflows.
- Application code, vendor assets, installed environment, tests, maintenance utilities, Git history and current documentation.
- Scientific validation sources, experiments and numerical comparisons: these remain useful evidence even when they are not loaded by the interface.

The before/after SHA-256 identities of all 179 regular files in data, Examples and Recipes matched. The archive inventory records the original location, new location, size, reason and hash of every moved regular file; moved hashes were verified. The complete inventory and scan classification are under the dated ToRemove folder. No permanent deletion occurred. Python and test caches can regenerate during normal use.

The cleanup does not make scientific validation claims. The media/UI and protected-input checks are recorded in `validation/about-video-cleanup.json`.

Post-verification pytest cache was also moved to the inventory’s `verification-caches/` subfolder. Verification: 6 release-maintenance tests and all 284 frontend tests passed; all 7 examples report ready with 31 protected inputs, media/seek-range requests passed, all tabs opened, and no active Markdown links target the archive or missing local files.
