# Mission reference review and L-band scope

This review documents the Mission Library’s explanations and source links.

## Source assessment

| Supplied source | Reviewed content | Incorporated and qualified |
|---|---|---|
| Nisar.docx | Italian briefing on GSLC, GCOV, GUNW, GOFF and complementary applications | Product roles and band distinction. Corrected S-band wavelength, phase-cycle limit, scattering claims, geocoding limits, unsupported GSLC and general Earthdata/SDK scope. This briefing is not a product specification. |
| Earth Science Applications with NISAR · Das et al. · ISRO/SAC · InGARSS, 13 December 2025 | One-page poster: instrument table, observation plans, product diagram, ISRO plans and S-band sample illustrations | L/S frequency table, joint-acquisition distinction, polarization/mode dependence and the separation of planned mission applications from implemented features. The poster’s ISRO L3 mosaics/L4 plans are not the NASA SME2 hierarchy. Original PDF is library reference 99. |
| NISAR and Applications of SAR Interferometry · Batuhan Osmanoglu · NASA Goddard | 24 slides including presenter notes: amplitude/phase/coherence, interferometry, VLM and historical examples | Phase and LOS concepts, GNSS reference requirements, local/model assumptions. Slide 5’s planned 2022 launch is obsolete. Slides 11–16/22–24 describe earlier radar work; figures are not NISAR validation. Daily-volume and product-suite slides are historical design material. Original PDF is library reference 100. |

The PDFs remain unchanged and attributed. Their app links point to two exact bundled reference paths; no general file-browser or data-folder access is added. Nisar.docx was reviewed for content, not republished as an authoritative guide. Source text extraction and file hashes are retained under `docs/validation/mission-band-review/`.

## Important corrections

- **S-band:** about 9.4 cm at 3.2 GHz, not 12 cm. **L-band:** about 24 cm at 1.257 GHz. The labels refer to different radar instruments, while frequency A/B refer to subbands.
- **Archive scope:** ASF distributes mission L-band products, including processed L-band observations from joint acquisitions. The poster’s brief L-only/joint archive split should not be taken to exclude all joint-acquisition L-band data from ASF. Current access guidance takes precedence.
- **Credentials and SDKs:** Earthdata Login authorizes access to many NASA collections. earthaccess/asf_search are not intrinsically L-band-only. This app’s configured collections and LSAR readers establish its supported inputs.
- **S-band availability:** verify the current Bhoonidhi release rather than assuming every L-band product has an available S-band counterpart. ASF’s reviewed availability page lists a limited RSLC/GSLC/GCOV S-band sample release from January–February 2026. No S-band ingestion was added.
- **Geocoding:** puts measurements on map grids; it does not remove all atmospheric, unwrapping, shadow or layover errors. UTM is not the only projection.
- **GCOV:** diagonal terms describe power; off-diagonal covariance can preserve relative polarimetric phase. It is not simply an image with all phase relationships removed.
- **GUNW:** unwrapped phase can span multiple cycles. The approximately 12 cm L-band range-change cycle is not a universal maximum displacement. Gradient, coherence, sampling and unwrapping matter; GOFF is complementary and can also fail.
- **Water and vegetation:** flooded vegetation may brighten, and canopy penetration is conditional. Neither a dark pixel nor L-band alone proves inundation or a visible stable ground return.
- **Mission versus app:** GSLC is a Level 2 mission product but is not an app input. SME2 is a NASA Level 3 retrieval. Hazard likelihoods, levee safety, biomass, depth, volume and planned L4 products are not automatically produced by this app.

## Current checks and source precedence

The actual code was inspected: `backend/catalog.py` selects named NASA NISAR collections; the import/reader paths use `/science/LSAR/`. Original and subset inputs follow the same band scope. These behaviors were documented, not broadened. Login handling and credential storage were not changed.

Current product specifications and archive release notes take precedence over historical teaching slides, poster plans and the team briefing. Sources checked:

- [ASF NISAR access overview](https://nisar-docs.asf.alaska.edu/access-overview/)
- [ASF available data and release notes](https://nisar-docs.asf.alaska.edu/availability-overview/)
- [ASF product hierarchy and maturity](https://nisar-docs.asf.alaska.edu/products-overview/)
- [NASA/JPL instrument description](https://nisar.jpl.nasa.gov/mission/observatory/radars/)
- [ISRO NISAR utilization programme](https://www.sac.gov.in/data/Event/524/NISAR_Utilization_Programme_Jul_2023.pdf)
- [ISRO Bhoonidhi NISAR portal](https://bhoonidhi.nrsc.gov.in/NISAR/)

This is a documentation update. The new local-reference allowlist is checked against path traversal and arbitrary local URLs; all **138 frontend tests and 302 backend tests pass**. A stale P02 version assertion was aligned with the already installed 0.5.0 method. The app’s processing algorithms and earlier numerical results are unchanged.

## Supplied Science Users’ Handbook

The supplied `NISAR_FINAL_9-6-19.pdf` has an August 2019 Version 1 cover and a 2018 suggested citation in its front matter. It is a historical prelaunch source, with 139 PDF pages containing many two-page spreads and printed numbering through 261. A byte-identical copy is bundled at `frontend/assets/library/sources/nisar-science-handbook-2019.pdf` as the existing reference 53. The existing second-edition DOI reference 70 is retained, with an additional friendly link to NASA’s updated handbook landing page in the reading chapter; current NASA mission facts are reference 103. The source directory reuses the two existing handbook records. These sources are distinguished rather than treating the historical handbook as a current product specification.

Reviewed areas: instrument design / SweepSAR (4.7); products (5); inundation (6.4); errors (7); calibration/validation (8); SAR, polarization and InSAR concepts (15.1). The library adds four chapters and expands hardware/coverage explanations. Design requirements are not presented as achieved app accuracy or current delivery guarantees.

| Extract | Original printed page | PDF page | App asset |
|---|---|---|---|
| Figure 4-10 · SweepSAR | 40 | 27 | `frontend/assets/library/handbook/sweepsar.png` |
| Figure 6-9 · inundation workflow | 84 | 49 | `frontend/assets/library/handbook/inundation-workflow.png` |
| Figure 15-3 · LOS motion geometry | 155 | 84 | `frontend/assets/library/handbook/insar-motion.png` |

Figures were cropped from rendered supplied pages, without changing their scientific content. New captions retain their source and explain interpretation limits. The SweepSAR caption preserves the warning that the along-track separation is illustrative. The inundation caption makes clear that the complete proposed classifier is not implemented. Phase conversion is explained as a magnitude relation because sign depends on product conventions and phase ordering.

Current facts were checked at [NASA mission overview](https://science.nasa.gov/mission/nisar/) and [updated handbook page](https://science.nasa.gov/mission/nisar/nisar-handbook/), with current [ASF product guidance](https://nisar-docs.asf.alaska.edu/products-overview/). Actual launch remains 30 July 2025 and S-band is about 9.4 cm. The old limited-S-band-sample wording was replaced with NASA’s current report of daily processed S-band products through Bhoonidhi; this app remains L-band-only. No complete second-edition PDF review is claimed.

Frontend checks cover safe local PDF/page links, figure packaging/captions, historical-versus-current facts, method boundaries and accessible rendering. The handbook sync script can be reapplied after other library rebuild steps without duplication. No processor, data-selection setting, credential handling or Earthdata session was changed.
