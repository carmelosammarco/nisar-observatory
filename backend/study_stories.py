"""Curated interpretation prompts, separate from measured run findings.

These explanations reuse the existing case references. They are hypotheses and
reading guidance, never an automatic physical classification or accuracy claim.
"""
STORIES = {
 'P01': {
  'question':'Where did new water candidates appear?',
  'audience':'Floodplain observers, educators and water-resource teams',
  'context':'The Chókwè floodplain in Mozambique provides an intuitive comparison between two radar observations twelve days apart.',
  'driver':'Floodplain inundation is a plausible explanation for new dark radar returns where NASA’s dated flood visualization shows water expansion.',
  'alternatives':['Smooth dry ground and radar shadow can also have low returns.','Flooded vegetation may brighten and escape this open-water rule.'],
  'confirm':'Use independently mapped inundation on the same dates and footprint. Add later observations to investigate a return to dry.',
  'use':'Identify locations for closer inspection and compare the result with independent flood evidence. Do not infer water depth, damage or a safe route.',
  'exercise':'Change the single-channel threshold by 1 dB, rerun, and compare candidate area on the same footprint.',
 },
 'P02': {
  'question':'How often did this wetland meet the water-candidate rule?',
  'audience':'Wetland researchers, resource managers and learners',
  'context':'Six Wheeler Marsh observations sample different wetland states. Nearby tide information provides context, not a direct water-level measurement at every radar cell.',
  'driver':'Tidal inundation can change the radar response of exposed water, mud and marsh vegetation.',
  'alternatives':['Vegetation structure, wetness and roughness can change radar brightness.','A nearby tide gauge may not represent local marsh water levels at acquisition time.'],
  'confirm':'Compare acquired times with local water-level observations and independent inundation labels. Historical paper accuracy does not transfer to NISAR.',
  'use':'Explore spatial wetness patterns and sampling gaps. Acquisition frequency is not continuous hydroperiod, depth or volume.',
  'exercise':'Shift an HH or HV threshold, keep the same six observations, and examine where occupancy changes.',
 },
 'P03': {
  'question':'Where did surface scattering change around the fire?',
  'audience':'Fire researchers, land managers and educators',
  'context':'Timber Fire uses separate pre-event HH/HV baselines for each viewing group and compares candidate change with published results and an official incident boundary.',
  'driver':'Fire-related changes in vegetation and exposed ground can alter HH and HV scattering relative to the observed baseline.',
  'alternatives':['Moisture, other vegetation change and terrain effects can also affect the score.','Different views may have different comparison dates; the fused map is not a synchronized observation.'],
  'confirm':'Inspect dated independent imagery, the official perimeter and unburned islands. A perimeter is an operational proxy, not perfect pixel truth.',
  'use':'Prioritize candidate surface-change patches for investigation. The scene-relative score is not burn severity or recovery.',
  'exercise':'Change only the score threshold, rerun, and inspect the candidate-area difference without changing the normalization domain.',
 },
 'P04': {
  'question':'Where did the ground move relative to the selected reference?',
  'audience':'Ground-motion researchers, educators and infrastructure analysts',
  'context':'The Mexico City example reconstructs acquired dates from six connected interferometric pairs and fits a relative line-of-sight trend.',
  'driver':'The spatial pattern is consistent with the subsidence discussed in NASA’s Mexico City example; this processing measures relative radar line-of-sight motion.',
  'alternatives':['Horizontal motion also contributes to LOS displacement.','Atmosphere, unwrapping and motion of the reference can affect the estimated trend.'],
  'confirm':'Use time-matched GNSS or an independently processed displacement grid, with compatible reference and viewing geometry.',
  'use':'Inspect relative movement patterns and locations needing further geodetic study. Annualized LOS rate is not direct vertical subsidence or a full year of observations.',
  'exercise':'Compare a second independently justified reference with the original, retaining the same pairs and annualized units.',
 },
 'P05': {
  'question':'What ground-motion evidence brackets the earthquake?',
  'audience':'Earthquake researchers, educators and geospatial analysts',
  'context':'Three northern Venezuela views cover the event interval. Their original dates, viewing geometry, reference treatment and overlap differences remain inspectable.',
  'driver':'Earthquake-related deformation is a plausible contributor to the event-bracketing LOS pattern described in NASA’s publication.',
  'alternatives':['The intervals may also contain other motion and atmospheric effects.','Different view geometry or reference origins can produce seams and overlap differences.'],
  'confirm':'Inspect single-group results, overlap diagnostics, event timing and independently matched displacement measurements.',
  'use':'Explore deformation evidence and decide where source-by-source checks are needed. This is not a damage or hazard map.',
  'exercise':'Change a justified coherence threshold, retain event timing and references, then compare valid coverage and displacement on common cells.',
 },
 'P06': {
  'question':'Where and when did radar scattering depart from the baseline?',
  'audience':'Volcano researchers, educators and remote-sensing learners',
  'context':'Five Krasheninnikov acquisitions show signed radar changes beside NASA’s dated volcano frames. The baseline may already contain ongoing eruption effects.',
  'driver':'New volcanic surface material can change roughness and scattering, but brightness alone cannot isolate lava.',
  'alternatives':['Snowmelt and surface wetness can produce strong brightness changes.','Terrain and viewing geometry can influence the observed pattern.'],
  'confirm':'Use independently dated lava outlines, thermal or optical observations and snow/weather evidence before attributing candidate patches to lava.',
  'use':'Find acquired dates and patches worth investigating. Repeated detections do not establish continuous activity or validated lava extent.',
  'exercise':'Change the signed-change threshold, keep baseline and smoothing fixed, and compare the latest departure and candidate patches separately.',
 },
 'P07': {
  'question':'How fast might the glacier be moving horizontally?',
  'audience':'Glacier researchers, educators and mountain-environment teams',
  'context':'A Samudra Tapu offset pair and delivered viewing geometry produce a constrained horizontal-speed estimate for comparison with published flow maps.',
  'driver':'Ice flow is consistent with a faster glacier trunk and slower margins, subject to the offset and viewing-geometry assumptions.',
  'alternatives':['Matching errors and poor geometry can create apparent motion.','Vertical motion and the chosen geometry height can bias the constrained horizontal solution.'],
  'confirm':'Compare a contemporaneous independent velocity raster or field measurements on matched support; a similar colour pattern or maximum is insufficient.',
  'use':'Investigate flow patterns under the explicit zero-vertical-motion constraint. A short-pair annualized speed does not measure a full year.',
  'exercise':'Vary the geometry-height assumption within a justified range and compare horizontal speed and conditioning on identical inputs.',
 },
}


def story(method):
 import copy
 return copy.deepcopy(STORIES.get(method,{
  'question':'What do the declared measurements show?',
  'audience':'People exploring a new processing hypothesis',
  'context':'This is an experimental sequence. Its findings describe the selected measurements and settings.',
  'driver':'A physical explanation requires independent evidence appropriate to the measurement.',
  'alternatives':['Acquisition geometry, quality screening, sampling and processing choices can affect the result.'],
  'confirm':'Inspect the executed steps and compare independent observations on compatible dates and support.',
  'use':'Explore a hypothesis and preserve the exact recipe. A valid workflow is not a validated environmental detector.',
  'exercise':'Change one parameter at a time and compare compatible results on identical spatial support.',
 }))


def general_story(method):
 """Interpret a measurement without assigning another region's event/context."""
 value=story(method)
 value['context']='This study uses the selected location and observations. Published example agreement does not establish the cause or accuracy of this new result.'
 drivers={
  'P01':'Expansion of open water can produce new dark radar returns. A flood interpretation requires independently dated evidence for this location.',
  'P02':'Changes in exposed water, vegetation and surface wetness can alter the fraction of acquisitions meeting the rule. A tidal interpretation requires local water-level and acquisition-time evidence.',
  'P03':'Changes in vegetation, exposed ground or moisture can change HH and HV scattering. Fire is one hypothesis only when independently documented in this region and interval.',
  'P04':'Referenced LOS phase changes can contain ground movement, atmospheric effects and processing errors. A subsidence mechanism requires independent local context and suitable geometry.',
  'P05':'An event-bracketing LOS interval can include earthquake deformation and other motion or propagation effects. Event timing alone does not establish that all mapped displacement was coseismic.',
  'P06':'Changes in surface material, snow, moisture or roughness can alter radar brightness. Lava attribution requires independent local eruption evidence.',
  'P07':'If independent context identifies glacier ice, coherent offset patterns may reflect flow. Matching errors, viewing geometry and the vertical-motion constraint must still be checked.',
 }
 value['driver']=drivers.get(method,value['driver'])
 if method=='P02':value['alternatives']=['Vegetation, wetness and roughness can affect radar brightness.','Sampling gaps or an unrepresentative local water-level record can obscure the actual wetland state.']
 value['exercise']='Keep the observations and study area fixed, change one scientifically justified setting, rerun and compare compatible outputs on jointly valid cells.'
 return value
