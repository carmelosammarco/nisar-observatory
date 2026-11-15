# Data and interface sources

- NISAR mission science data: NASA / ISRO; NASA ASF distribution. Granule identifiers and source array paths are preserved in every result. Official product guide: https://nisar-docs.asf.alaska.edu/
- Leaflet 1.9.4: BSD-2-Clause, https://github.com/Leaflet/Leaflet/blob/v1.9.4/LICENSE . Bundled locally.
- Plotly.js Basic 2.35.2: MIT, https://github.com/plotly/plotly.js/blob/v2.35.2/LICENSE . Bundled locally.
- Natural Earth 1:110m country boundaries: public domain, https://www.naturalearthdata.com/about/terms-of-use/ . Bundled from the project's vector repository: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson . Small-scale geographic context only, not precise scientific boundaries.
- Esri World Imagery background service: Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community. Service metadata: https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer . Interactive background tiles are requested directly by the browser and not bulk downloaded. Source attribution is shown on the map.
- Mission explanations retain useful cited source material in the Mission library. Historical architecture/research/source-register pages are no longer separate library tabs. See also the root THIRD_PARTY_NOTICES.md for distribution scope.

The conceptual orbital diagram and interface styling were created for this application. It is not an official NASA or ISRO product.


Mission-library illustrations: the local NISAR spacecraft rendering in `frontend/assets/library/nisar-spacecraft.png` is credited to NASA/JPL-Caltech and comes from the prior research guide, whose source is https://www.jpl.nasa.gov/press-kits/nisar/mission-overview/spacecraft/ . The product-flow figure was created for the team research guides. The route-card line illustrations were created in SVG for this application. These diagrams are conceptual explainers, not observed radar imagery or scientific results.


### P04 Mexico City comparison (0.4.0)

The verification figure reproduces the previously downloaded NASA reference illustration [PIA26709](https://www.jpl.nasa.gov/images/pia26709-us-indian-spacecraft-captures-mexico-city-subsidence/), credited to NASA/JPL-Caltech/David Bekaert, beside the app’s independently calculated raster from NASA/ISRO NISAR originals. The existing background image is credited to Esri, Vantor, Earthstar Geographics and the GIS User Community. The comparison is qualitative; it does not imply NASA endorsement or independent validation of app accuracy. Figure scripts reuse local reference assets and do not download new imagery.


### Mexico rainbow lookup (0.4.1)

`backend/mexico_palette.json` contains 256 RGB samples of Matplotlib 3.11.2’s Jet colormap, matching the scientific comparison figure. The runtime reads this static lookup and does not require Matplotlib for the app display. See [Matplotlib colormap guidance](https://matplotlib.org/stable/users/explain/colors/colormaps.html) for rainbow-map perceptual limits; the standard diverging palette remains available. This color choice does not imply NASA approval or numerical accuracy.

### Reproducible Examples (0.5.0)

The Examples folders retain NASA/ISRO NISAR L-band subset provenance and exact NASA/ASF granule identities. Chókwè’s published reference screenshots are credited to NASA SVS / Zoey N. Armstrong (Navteca), [SVS 5661](https://svs.gsfc.nasa.gov/5661/). Mexico City references NASA/JPL-Caltech/David Bekaert’s PIA26709. Venezuela references NASA Earth Observatory’s earthquake illustration and a USGS event record. Wheeler Marsh cites the original Remote Sensing papers and NOAA measured tide context; the included new radar maps were calculated by this app and are not reproductions of those papers’ historical PALSAR maps. Costa Marques uses official INPE DETER boundaries and Sentinel-2 imagery distributed by Element 84; the example links the individual optical items and methodology. Derived comparison figures retain their captions and evidence limitations. Basemap screenshots retain the Esri imagery attribution visible in their interface. Full source links and individual descriptions appear in each tutorial. Inclusion does not imply agency endorsement.

## Supplied 2019 NISAR Science Users’ Handbook

The user-supplied historical NASA/JPL-Caltech / NASA-ISRO science-team handbook is bundled unchanged as `frontend/assets/library/sources/nisar-science-handbook-2019.pdf`. Three diagrams are cropped excerpts (figures 4-10, 6-9 and 15-3), with explicit handbook attribution, original printed page numbers and links to the full local source. They illustrate concepts; they are not app-generated science results. Names and original publication credits remain with their source authors. See `MISSION_SOURCE_REVIEW.md` for the extraction and current-fact review.

### Selectable basemaps and reference labels · 21 October 2026

The browser requests tiles directly for the current view; the application does not bulk-download or package map tiles. Optional single-result PNG exports compose a bounded set of the selected service’s tiles, with source credits printed on the image and embedded in metadata. Attribution remains visible on the map.

- Satellite: [Esri World Imagery service](https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer), credited to Esri, Vantor, Earthstar Geographics and the GIS User Community.
- Light and Dark: [World Light Gray Base](https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer) and [World Dark Gray Base](https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer). Reference labels use the matching `World_Light_Gray_Reference` / `World_Dark_Gray_Reference` services. Credits from the service metadata: Esri, HERE, Garmin, © OpenStreetMap contributors and the GIS user community.
- Satellite reference labels: [World Boundaries and Places](https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer), with the same reference-layer credits. Plain optionally uses Light Gray Reference labels.
- Streets: [Esri World Street Map](https://services.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer). Credits: Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), Esri Korea, Esri (Thailand), NGCC, © OpenStreetMap contributors and GIS User Community. This replaces direct OSM public tiles, whose [tile policy](https://operations.osmfoundation.org/policies/tiles/) requires a referrer; the application keeps its no-referrer policy. Attribution follows the active provider. There is no bulk/offline prefetch.
- Plain adds no third-party background tiles when labels are off. The existing Natural Earth outline fallback is hidden for this background.

Esri services retain their [terms of use](https://www.esri.com/en-us/legal/terms/full-master-agreement). No new CARTO or other paid-provider key is configured. Background/label availability and imagery dates are separate from NISAR science-data access and acquisition dates.

### Optional PNG background composition

A PNG export may request only the fixed allowlisted Esri services above. Each map image is limited to 36 base tiles and up to 36 reference tiles, with bounded request timeouts and image dimensions, four concurrent requests, redirect rejection and a small in-memory LRU cache. No arbitrary URL, Earthdata session or user credential is sent to a background provider. PNG metadata records the chosen style, labels, radar opacity, source attribution and exact Mercator extent. Exporting a presentation image does not modify numeric science rasters or their georeferencing.
