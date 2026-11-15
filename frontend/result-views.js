/* Curated map views. All original saved layers remain in the download library. */
const mainResultOrder={LAB:['summary','change'],P01:['event','recovery','unresolved'],P02:['occupancy'],P03:['fire_score','fire_candidate','relative_change'],P04:['los_rate_year','los_change'],P05:['range'],P06:['latest_departure','surface','confirmed_change','change_direction','largest_step'],P07:['radar_magnitude','value','change','variability']};
const resultCategoryInfo={main:{title:'Main results',intro:'Start with the tool’s main findings. These are selected views of the measurements; read the interpretation below before assigning a cause.'},time:{title:'Explore time',intro:'Choose an acquired date or measured interval, or play the sequence. Unobserved times are not filled in. P04 connected histories are reconstructed at acquired dates.'},quality:{title:'Quality & reliability',intro:'Check the reference, valid coverage, sensitivity and fit. These maps help judge the evidence; they do not establish independent scientific accuracy.'},advanced:{title:'Advanced maps',intro:'Inspect original intervals, alternative calculations and measurement context. These are supporting views, and some repeat information in the main results.'}};
function indexedResultLayers(result=state.result){return (result?.layers||[]).map((layer,index)=>({...layer,index}))}
function p04RateLayer(result=state.result){const preferred=state.p04RateUnit==='cm/month'?'los_rate_month':'los_rate_year';return indexedResultLayers(result).find(l=>l.id===preferred)||indexedResultLayers(result).find(l=>['los_rate_year','los_rate_month'].includes(l.id))}
function selectedEventFrame(result){
 const frames=indexedResultLayers(result).filter(l=>l.id.startsWith('observation_')),selected=result.extra?.selected_interval;
 if(selected){const exact=frames.find(l=>l.start===selected.start&&l.end===selected.end);if(exact)return exact}
 const event=result.processing_options?.event_date||state.currentJob?.request?.options?.event_date;
 return event?frames.find(l=>(l.start||'').slice(0,10)<event&&event<(l.end||'').slice(0,10)):null;
}
function resultViewGroups(result=state.result){
 const project=result?.extra?.workflow_method||result?.project;const all=indexedResultLayers(result),byId=new Map(all.map(l=>[l.id,l]));let wanted=[...(mainResultOrder[result?.extra?.workflow_method||result?.project]||[])];
 if(project==='P04')wanted=p04RateLayer(result)?[p04RateLayer(result).id,'los_change']:['range','interval_rate'];
 if(project==='P05'&&byId.has('event_displacement_cm'))wanted=['event_displacement_cm'];
 else if(project==='P05'){const event=selectedEventFrame(result);if(event)wanted=[event.id]}
 if(result?.extra?.surface_method)wanted=['latest_departure','surface',...(result.extra.surface_method.repeated_latest_available?['confirmed_change']:[])];
 if(result?.extra?.horizontal_velocity)wanted=['horizontal_speed','horizontal_change'];
 if(!result?.extra?.horizontal_velocity&&project==='P07'&&all.filter(l=>l.id.startsWith('observation_')).length<2)wanted=[...(byId.has('radar_magnitude')?['radar_magnitude']:[]),'value'];
 let main=wanted.flatMap(id=>byId.has(id)?[byId.get(id)]:[]);
 // Older runs can retain only a dated measurement or a generic change layer.
 if(!main.length){const fallback=byId.get('change')||all.find(l=>l.id.startsWith('observation_'))||byId.get('value')||byId.get('range');if(fallback)main=[fallback]}
 if(byId.has('workflow_output'))main.unshift(byId.get('workflow_output'));
 const mainIds=new Set(main.map(l=>l.id)),time=all.filter(l=>l.id.startsWith('observation_')).sort((a,b)=>(a.frame_index??Number(a.id.split('_')[1]))-(b.frame_index??Number(b.id.split('_')[1])));
 const isQuality=l=>l.id.startsWith('horizontal_condition_')||l.id.startsWith('horizontal_vertical_sensitivity_')||l.id.startsWith('quality_')||l.id.startsWith('offset_rejected_')||/^group_\d+_(count|reference_support|quality_|network_residual)/.test(l.id)||['event_coverage','event_source','event_overlap_spread','count','view_count','reference_support','threshold_sensitive','water_state','los_fit_residual','los_pair_residual','network_residual','seasonal_residual'].includes(l.id);
 const quality=all.filter(l=>!mainIds.has(l.id)&&isQuality(l)),qualityOrder=['reference_support','count','los_fit_residual','los_pair_residual','threshold_sensitive','water_state'];
 quality.sort((a,b)=>(qualityOrder.includes(a.id)?qualityOrder.indexOf(a.id):99)-(qualityOrder.includes(b.id)?qualityOrder.indexOf(b.id):99));
 const aliases=project==='P04'?all.filter(l=>['los_rate_year','los_rate_month'].includes(l.id)&&!mainIds.has(l.id)):[];
 const advanced=all.filter(l=>!mainIds.has(l.id)&&!l.id.startsWith('observation_')&&!isQuality(l)&&!aliases.some(alias=>alias.id===l.id));
 return {main,time,quality,advanced,aliases};
}
function qualityResultTitle(layer){
 const metric=layer.id.replace(/^quality_/,'').replace(/_\d+$/,'');
 const names={accepted_fraction:'Native samples kept',missing_fraction:'Missing native samples',coherence:'Coherence on accepted samples',snr:'Matching score on accepted samples',ionospheric_phase_correction:'Delivered ionospheric phase correction',rejected_coherence:'Low-coherence samples excluded',rejected_component_missing:'Missing connected-component labels excluded',rejected_other_component:'Other connected components excluded',rejected_source_mask:'Source-mask exclusions',rejected_nonpositive_power:'Non-positive radar power excluded',rejected_snr:'Low matching-score samples excluded',rejected_unpaired_offset:'Samples missing a matching offset component',rejected_missing_correction:'Missing correction samples excluded',rejected_physical_bounds:'Out-of-range retrievals excluded',rejected_quality_retrievalqualityflag:'Retrieval recommendation exclusions'};
 if(!names[metric])return null;
 const date=layer.label?.split(' · ').at(-1);return names[metric]+(date&&date!==layer.label?' · '+date:'');
}
function friendlyResultTitle(layer,result=state.result){
 if(layer.id.startsWith('quality_')){const title=qualityResultTitle(layer);if(title)return title}
 if(result?.project==='P04'&&['los_rate_year','los_rate_month'].includes(layer.id))return 'Relative motion rate';
 if(result?.project==='P05'&&layer.id===selectedEventFrame(result)?.id)return 'Relative change across the event interval';
 if(result?.extra?.surface_method){const names={surface:'Changed patches at the latest date',change_direction:'Latest brightening or dimming',confirmed_change:'Latest change repeated on consecutive dates',first_change:'First observed qualifying change',repeat_count:'Consecutive dates supporting the latest change',latest_departure:'Latest smoothed change from baseline'};if(names[layer.id])return names[layer.id]}
 const names={event_displacement_cm:'Displacement across the earthquake interval',event_source:'Source group used at each map cell',event_coverage:'Number of event groups covering each cell',event_overlap_spread:'Difference between overlapping LOS views',los_change:'Total change over the observed period',los_fit_residual:'Departure from the fitted motion trend',los_pair_residual:'Pair-network reconstruction residual',network_rate:'Additional network trend',network_residual:'Network fit residual',annual_amplitude:'Annual-model amplitude',seasonal_residual:'Annual-model fit residual',interval_rate:'Selected interval · average relative rate',interval_rate_spread:'Variation between interval rates',moisture_anomaly:'Latest moisture versus the selected-record median',wetting_steps:'Observed wetting steps',drying_steps:'Observed drying steps',change_direction:'Persistent brightening or dimming',largest_step:'Date index of the largest scattering step',recovery_lower_days:'Last observed wet state · days after comparison',recovery_upper_days:'First observed dry state · days after comparison',unresolved:'New water without an observed return to dry',threshold_sensitive:'Sensitivity to the water threshold',water_state:'Latest water classification and ambiguity',baseline_departure:'Latest scattering versus the declared baseline',standardized_departure:'Baseline departure relative to robust spread',polarization_ratio_change:'Change in polarization contrast',water_gains:'Observed dry-to-water switches',water_losses:'Observed water-to-dry switches'};
 return names[layer.id]||layerTitle(layer)||layer.id;
}
function customSummaryContext(result){
 const recipe=result?.extra?.workflow,steps=recipe?.steps||[],last=steps.at(-1),count=result?.series?.length||result?.metrics?.observations||0;
 if(recipe?.method!=='custom'||last?.operation!=='summary'||last.parameters?.statistic!=='mean')return '';
 const baseline=steps.findIndex(s=>s.operation==='baseline');
 if(count===2&&baseline>=0&&(steps[baseline].parameters?.count??1)===1&&steps.slice(baseline+1,-1).every(s=>s.operation==='smooth'))return ' This mean includes the first observation, which becomes zero after baseline subtraction. With these two dates, the mean map is half the first-to-last change on common valid cells. Choose “Change from first to last date” to inspect the full observed difference.';
 if(baseline>=0)return ' The mean includes the baseline observations too; it is not simply the latest change. Use the dated maps and first-to-last difference to understand the comparison.';
 return '';
}
function extraLayerExplanation(layer,result){
 const id=layer.id;
 if(layer.trace_operation)return layer.interpretation||'Captured intermediate measurement. Read its own units, support and dates; this is not an independent finding.';
 if(id==='workflow_output'||id.startsWith('workflow_post_'))return 'Additional declared map operations applied to the chosen original method layer. The original timeline, method maps and statistic cards are retained separately; read the added-output statistics and recipe for this experimental map.';
 if(result?.extra?.workflow&&result.extra.workflow.method==='custom'){
  if(result.extra?.trend_fit&&id==='summary')return 'This overview is the fitted LOS-rate map after any later declared steps. It is a single spatial result, not an average of pair rates. The timeline retains reconstructed acquired-date displacements in cm; the rate uses the units shown here. Read the fit and pair residuals before interpreting it as ground motion.';
  if(result.extra?.network_reconstruction&&id==='change')return 'Latest minus first reconstructed acquisition date, in the stated displacement units. The connected pair network and fixed ground reference define this relative LOS record. It is not direct vertical subsidence.';
  if(id==='summary')return 'A spatial map of the declared summary across the final processed observations, using only cells valid on every selected date. Mean, median and spread are in the stated units; candidate frequency is a fraction of usable observations, not elapsed time flooded.'+customSummaryContext(result);
  if(id.startsWith('step_'))return 'Intermediate workflow output saved after the labelled processing step. Latest maps use the final selected observation; baseline maps show the declared observed baseline. Compare this layer with later steps and native quality before attributing a physical cause.';
  if(id==='change')return 'Final processed observation minus the first, restricted to the common valid footprint. For GUNW and GOFF this compares separate pair intervals; it does not accumulate motion. Units reflect the chosen conversions and baseline steps. The summary statistic cards still describe the declared overview, not the currently displayed difference map.';
 }
 if(id==='horizontal_speed'||id.startsWith('observation_')&&result.extra?.horizontal_velocity)return 'Estimated horizontal speed from the two radar offsets and the native per-cell viewing vectors, with vertical velocity fixed at zero. Geometry uses the saved constant ellipsoidal height. Slope-parallel motion, vertical change, residual registration and offset noise can bias the estimate. Missing or ill-conditioned geometry stays blank. m/year is an annualized pair rate.';
 if(id==='horizontal_change')return 'Latest minus first estimated horizontal speed on cells usable in both intervals. It inherits the zero-vertical-velocity assumption and measurement errors; it is not accumulated displacement.';
 if(/^horizontal_east_/.test(id)||/^horizontal_north_/.test(id))return 'Constrained horizontal velocity component in geographic East/North/Up coordinates: positive is eastward or northward, respectively. Vertical velocity was assumed zero. m/year annualizes the measured interval; inspect geometry and the vertical-motion scenario.';
 if(/^horizontal_bearing_/.test(id))return 'Estimated horizontal flow direction clockwise from true north: 0° north, 90° east, 180° south, 270° west. Direction is undefined at zero speed and sensitive to offset noise. This is a circular angle, not a speed.';
 if(/^horizontal_condition_/.test(id))return 'Condition number of the per-cell two-by-two viewing matrix. Larger values amplify offset errors more strongly. Values above the configured maximum are excluded from horizontal speed; this is not a calibrated uncertainty map.';
 if(/^horizontal_vertical_sensitivity_/.test(id))return 'Magnitude of possible horizontal-vector bias if actual vertical velocity differs from the assumed zero by the saved scenario. This is a model-sensitivity bound for that scenario, not a confidence interval, measured error or correction.';
 if(id==='radar_magnitude'||/^radar_filtered_\d+$/.test(id))return 'The norm of the two radar components after each passes the configured spatial filters, on cells where both remain usable. Optional stable-ground correction is applied separately to both components. This is radar-plane motion, not horizontal glacier speed; vertical motion and measurement noise contribute. A positive norm alone does not prove glacier flow. Annualized m/year extrapolates the measured pair interval.';
 if(/^other_filtered_\d+$/.test(id))return 'The companion radar component after the same configured screening procedure, with its own cutoff and optional stable-ground bias, restricted to joint valid support. Read the saved source paths to identify range versus along track.';
 if(result.extra?.surface_method){const explain={surface:'1 marks a latest-date brightness change meeting the signed threshold and minimum patch area; 0 means this condition was not detected. It is not a lava boundary. Blank means no shared usable measurement.',confirmed_change:'Same-sign candidate change on at least two consecutive post-baseline acquisitions ending at the latest date. An apparent absence earlier does not exclude a late-growing patch. This does not establish continuous change between passes.',latest_departure:'Latest minus baseline radar brightness in dB, smoothed using the saved sigma on common valid support. Positive is brighter; negative darker. Snow, moisture, roughness and lava can all contribute.',first_change:'Index of the first later acquired date meeting the signed change and patch rules. Read the date key below. Blank means no qualifying observed change; onset is not known between passes.',repeat_count:'Number of consecutive post-baseline acquisitions ending at the latest date with the same qualifying sign. Zero means no latest candidate; one is a latest-only candidate, not independently confirmed change.',change_direction:'Latest qualifying direction: +1 brighter, −1 darker, 0 no retained candidate. Snowmelt and wetness can also cause these patterns.'};if(explain[id])return explain[id];if(id.startsWith('dated_departure_'))return 'Smoothed dB departure from the declared baseline at the labeled acquisition. These dated departures are supporting maps; Explore time shows the original calibrated radar brightness.';} 
 if(id==='fire_score')return 'Absolute HH and HV changes are added per viewing group, then the latest available views are averaged and smoothed. The score measures departure from the selected land window median in robust-spread units. It is not burn severity or a probability. Changing the area or land exclusions changes this spatial normalization.';
 if(id==='fire_candidate')return '1 identifies a change-score patch meeting the saved threshold and minimum area; 0 means the condition was not detected. Independent fire evidence is needed to call it burned. Blank means missing usable evidence, not unchanged ground.';
 if(id==='view_count')return 'Number of latest viewing groups contributing HH and HV together. One view can provide a value where another is invalid. More views do not certify accuracy; read each group’s dates and baseline.';
 if(id==='change_intensity'||id==='smoothed_intensity')return 'Nonnegative magnitude of HH plus HV change in dB, combined after separate per-view baselines. The smoothed version reduces speckle with the saved sigma. This is different from a signed change or a severity measurement.';
 if(result.extra?.fire_method?.id==='combined'&&id.startsWith('observation_'))return 'One post-baseline observation from its labelled viewing group: absolute HH plus absolute HV change in dB against that group’s baseline. These asynchronous snapshots are not the fused primary score and do not fill intervening dates.';

 if(result.project==='P05'&&id==='range')return 'The selected event-bracketing pair in the original mm unit, relative to its saved reference. It is the same interval quantity as the main centimeter map, with ten mm per cm. Positive is toward the satellite and negative away; it is not isolated earthquake damage.';
 if(result.project==='P05'&&id==='interval_rate')return 'Relative LOS change divided by the selected pair’s elapsed days, in mm/day. This is an average across the entire interval, not the speed of the earthquake rupture or a long-term velocity.';
 if(result.project==='P05'&&id==='reference_support')return 'Cells used to set each pair’s relative zero. In a mosaic this is the union of independently used reference cells; the per-group reference maps and table preserve their separate support. Valid phase and coherence do not establish stable ground.';
 if(id==='event_displacement_cm')return 'Relative LOS displacement in cm across the selected event-bracketing interval'+(result.extra?.event_mosaic?'s, with one source group selected at each cell. Inspect the source key and per-group dates/references.':' compared with the saved ground reference.')+' Positive is toward the satellite; negative is away. The active color key identifies the scale midpoint (zero for symmetric limits); blank coverage is missing evidence. The interval includes any other motion or atmospheric effects; it is not a damage map or east/up decomposition.';
 if(id==='event_source')return 'Integer source key for the group used at each cell. Read the source table for its track/frame, acquisition dates and reference support. Colors identify groups, not displacement severity.';
 if(id==='event_coverage')return 'Number of independently referenced event groups providing a valid measurement at each cell. Coverage describes evidence, not certainty; blank cells have no usable event measurement.';
 if(id==='event_overlap_spread')return 'Maximum minus minimum relative LOS displacement across overlapping groups, in cm. Differences include radar look direction, pair dates, reference offsets and processing errors; this is not an accuracy estimate. Blank means fewer than two valid views.';
 if(/^group_\d+_/.test(id)){const raw=id.replace(/^group_\d+_/,'');return 'One source group: '+(extraLayerExplanation({...layer,id:raw}, {...result,extra:{}})||'Supporting map in the labeled units. Read the source group, reference and interval in the event mosaic table. Different groups do not share one spatial reference support.')}
 if(id.startsWith('pair_'))return 'One original measured GUNW pair interval, converted to relative LOS change in mm using the saved reference. Read its start and end dates; it is not a cumulative history.';
 if(id.startsWith('offset_raw_'))return 'The primary radar-component interval rate after native SNR screening and before spatial outlier filtering. Compare it with the filtered dated view; a removed value can be noise or real localized motion.';
 if(id.startsWith('offset_rejected_'))return '1 marks values removed by spatial filtering; 0 marks retained values where a source measurement existed. This describes filtering decisions, not glacier change or a validated error map.';
 if(id.startsWith('other_component_'))return 'The other radar-component rate on its native SNR-screened support. The primary component’s extra spatial filtering and stable-terrain bias correction are not automatically applied here. It is not an east/north velocity.';
 if(id.startsWith('radar_magnitude_'))return 'Magnitude of the two screened radar-component rates before extra spatial filtering. Radar viewing coordinates are not geographic horizontal coordinates; this is not total glacier speed.';
 if(id.startsWith('quality_')){
  if(id.includes('ionosphere_interpolated'))return 'Fraction of native samples where the delivered ionosphere estimate was interpolated according to mask bit 24. This is correction provenance, not an earthquake signal or an automatic invalid-data flag.';
  if(id.includes('accepted_fraction'))return 'Fraction of native samples accepted before averaging into each analysis cell. Larger contributions support a more complete cell; high values do not prove scientific accuracy.';
  if(id.includes('missing_fraction'))return 'Fraction of native source samples with missing or non-finite measurements. Missing support is not zero environmental change.';
  if(id.includes('phase_correction'))return 'Delivered ionospheric phase correction in radians on accepted support. It is a correction term, not ground displacement. The run’s correction manifest records whether subtraction was requested.';
  if(id.includes('rejected_'))return 'Fraction of native samples excluded by the named screening rule before averaging. A high value means more data were rejected for that reason, not greater environmental change. Rejection fractions are rule-specific and need not sum to one.';
  if(id.includes('coherence'))return 'Mean coherence on accepted native support, on a 0–1 scale. Low coherence can limit phase interpretation; high coherence alone does not remove atmospheric errors or establish a stable reference.';
  if(id.includes('snr'))return 'Mean matching signal-to-noise score on accepted native support. Compare with the saved SNR threshold and coverage; this is not an independently measured displacement error.';
  return 'Source-quality or correction evidence for the labeled observation. Read the quantity and units; these values describe input suitability rather than a separate surface-change finding.';
 }
 const common={water_state:'Latest-date threshold classification: 0 is a dry candidate, 1 a water candidate, and 2 close enough to the threshold to be marked ambiguous. The ambiguity band is a sensitivity rule, not a calibrated probability.',baseline_departure:'Latest backscatter minus the per-cell median of the declared baseline dates, in dB. Positive means brighter and negative dimmer; it does not identify the environmental cause.',standardized_departure:'Baseline departure divided by robust baseline spread, with the saved noise floor. This is a contrast diagnostic, not a statistical significance score or confidence interval.',polarization_ratio_change:'Change in cross-polarized versus co-polarized power contrast between the first and last selected observations. Moisture, vegetation, roughness and geometry can contribute; no land-cover cause is assigned.',network_rate:'Fitted trend from the optional redundant phase-equivalent network, in mm/year. Inspect network support and residuals. Annualized units do not imply a year of data or direct vertical movement.',network_residual:'RMS mismatch of measured pair constraints with the network solution. It measures internal consistency, not independent accuracy.',annual_amplitude:'Amplitude of the fitted annual phase-equivalent oscillation, in mm, only when the acquired dates support the model. This is not active-layer thickness or thaw depth.',seasonal_residual:'RMS residual of the annual model, in mm. A small residual describes model fit; it does not prove a permafrost mechanism.'};
 if(common[id])return common[id];
 if(id==='count')return result.project==='P04'||['P05'].includes(result.project)?'Number of quality-screened measured pairs at each pixel. This is input coverage, not the number of reconstructed dates or an environmental change.':'Number of valid input observations at each pixel. Read this with changes and observation frequency; it is coverage rather than an environmental result.';
 if(id==='change'&&result.project==='P07')return 'Latest minus first radar-component interval-average rate, in m/day. This compares rates over separate intervals; it is not accumulated displacement or a direct acceleration estimate.';
 if(id==='value'&&result.project==='P07')return 'Latest filtered radar-component interval-average rate, in m/day. Check the labeled pair dates and screening evidence; this is not a geographic horizontal speed.';
 return null;
}
function syncCategoryPicker(layer){
 if(!state.result)return;
 if(['los_rate_year','los_rate_month'].includes(layer.id))state.p04RateUnit=layer.id==='los_rate_month'?'cm/month':'cm/year';
 const groups=resultViewGroups(),current=state.resultCategory||'main';
 const category=(groups[current]||[]).some(l=>l.id===layer.id)?current:['main','time','quality','advanced'].find(key=>groups[key].some(l=>l.id===layer.id))||'advanced';
 state.resultCategory=category;
 for(const key of ['main','time','quality','advanced']){
  const button=$('#result-category-'+key);if(button)button.setAttribute('aria-pressed',String(category===key));
 }
 const picker=$('#summary-choice'),label=$('#summary-choice-label');
 if(picker){picker.innerHTML=(groups[category]||[]).map(l=>`<option value="${l.index}">${esc(friendlyResultTitle(l))} · ${esc(l.unit||'')}</option>`).join('');picker.value=state.result.layers.indexOf(layer)}
 if(label)label.hidden=category==='time';
 if($('#result-category-description'))$('#result-category-description').textContent=resultCategoryInfo[category].intro;
 if($('#result-category-heading'))$('#result-category-heading').textContent=resultCategoryInfo[category].title;
 if($('#observation-player'))$('#observation-player').hidden=category!=='time';
 const rateVisible=state.result.project==='P04'&&category==='main'&&['los_rate_year','los_rate_month'].includes(layer.id);
 if($('#p04-rate-units'))$('#p04-rate-units').hidden=!rateVisible;
 if($('#p04-rate-unit'))$('#p04-rate-unit').value=layer.id==='los_rate_month'?'cm/month':'cm/year';
}
async function switchP05RateUnit(unit){
 if(!['cm/year','cm/month'].includes(unit))return;
 const target=state.result.layers.findIndex(l=>l.id===(unit==='cm/month'?'los_rate_month':'los_rate_year'));if(target<0)return;
 const before={low:displayLow,high:displayHigh,unit:state.displayUnit,category:state.resultCategory};stopTimeline();const current=state.layer;
 const factor=current?.unit==='cm/year'&&unit==='cm/month'?1/12:current?.unit==='cm/month'&&unit==='cm/year'?12:1;
 // Preserve the same physical custom range across a pure unit conversion.
 if(displayMode==='custom'&&current&&['los_rate_year','los_rate_month'].includes(current.id)&&Number.isFinite(displayLow)&&Number.isFinite(displayHigh)){
  displayLow*=factor;displayHigh*=factor;state.displayUnit=unit;
  if($('#display-low'))$('#display-low').value=displayLow;
  if($('#display-high'))$('#display-high').value=displayHigh;
 }
 state.p04RateUnit=unit;state.resultCategory='main';
 const ok=await selectLayer(target);
 if(ok===false&&current){displayLow=before.low;displayHigh=before.high;state.displayUnit=before.unit;state.resultCategory=before.category;state.p04RateUnit=current.id==='los_rate_month'?'cm/month':'cm/year';if($('#display-low'))$('#display-low').value=before.low;if($('#display-high'))$('#display-high').value=before.high;syncCategoryPicker(current)}
}
function resultValueText(value,layer,result){
 if(value===null)return 'No valid value';
 if(layer.unit==='observation index'){
  const extra=result?.extra||{},calendar=layer.id==='recovery'?extra.recovery_calendar:layer.id==='first_change'?extra.first_change_calendar:extra.step_calendar;
  const row=(calendar||[]).find(r=>r.index===Math.round(value));
  if(row)return (row.date?row.date.slice(0,10):row.start.slice(0,10)+' → '+row.end.slice(0,10))+' · observation index '+Math.round(value);
 }
 return value.toFixed(4)+' '+layer.unit;
}

function resultDisplayQuantity(layer,result){
 if(layer.trace_operation)return 'intermediate:'+layer.trace_operation+':'+layer.id.replace(/_[a-f0-9]{8}$/,'')+':'+layer.unit;
 if((result?.extra?.workflow_method||result?.project)==='P07'){if(layer.id==='horizontal_speed'||layer.id.startsWith('observation_')&&result.extra?.horizontal_velocity)return 'horizontal-speed:'+layer.unit;if(layer.id==='horizontal_change')return 'horizontal-speed-change:'+layer.unit;if(layer.id==='radar_magnitude'||/^radar_(filtered|magnitude)_\d+$/.test(layer.id))return 'radar-plane-norm:'+layer.unit;if(layer.id==='variability')return 'radar-component-spread:'+layer.unit;if(layer.id==='change')return 'radar-component-rate-difference:'+layer.unit;}
 if(layer.unit==='dB'){
  if(result?.extra?.fire_method?.id==='combined'&&(layer.id.startsWith('observation_')||['change_intensity','smoothed_intensity'].includes(layer.id)))return 'combined-change-magnitude';
  return layer.kind==='diverging'?'signed-backscatter-change':'radar-brightness';
 }
 return layer.unit;
}
