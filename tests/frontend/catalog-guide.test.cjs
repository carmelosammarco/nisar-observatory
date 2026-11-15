const {test}=require('node:test');
const assert=require('node:assert/strict');
const g=require('../../frontend/catalog-guide.js');
const box=b=>({boxes:[b],name:'scene',product:'GCOV',start:'2026-09-01T00:00:00Z',end:'2026-09-01T00:00:30Z'});
test('repeat observations do not inflate union coverage; four can cover more than eight',()=>{
 const aoi=[0,0,10,10];
 const small=Array.from({length:8},()=>box('0 0 10 2'));
 const large=Array.from({length:4},()=>box('0 0 10 8'));
 assert.equal(g.summary(small,aoi).percent,20);
 assert.equal(g.summary(large,aoi).percent,80);
});
test('combines partial bounds without counting overlap twice',()=>{
 assert.equal(g.coverage([[0,0,7,10],[3,0,10,10]],[0,0,10,10]),100);
 assert.equal(g.coverage([[20,0,30,10]],[0,0,10,10]),0);
});
test('coverage uses spherical latitude weighting',()=>{
 const expected=100*Math.sin(Math.PI/6)/Math.sin(Math.PI/3);
 assert.ok(Math.abs(g.coverage([[0,0,10,30]],[0,0,10,60])-expected)<1e-9);
});
test('missing and malformed footprints stay unknown, not full coverage',()=>{
 const items=[{name:'local',product:'GCOV'},box('bad'),box('0 0 NaN 5')];
 assert.equal(g.summary(items,[0,0,10,10]).percent,null);
 const partial=g.summary([...items,box('0 0 10 5')],[0,0,10,10]);
 assert.equal(partial.known,1);assert.equal(partial.total,4);assert.equal(partial.percent,50);
});
test('dateline bounds split into two real parts',()=>{
 const parts=g.boxes(box('-10 170 10 -170'));
 assert.deepEqual(parts,[[170,-10,180,10],[-180,-10,-170,10]]);
 assert.equal(g.coverage(parts,[175,-5,180,5]),100);
});
test('pair acquisition windows come from all four filename timestamps, not catalog extent',()=>{
 const d=g.windows({product:'GUNW',name:'NISAR_L2_PR_GUNW_031_113_D_079_032_4000_SH_20260926T011329_20260926T011403_20261008T011329_20261008T011403_P05023_N_F_J_001',start:'wrong',end:'wrong'});
 assert.deepEqual(d.reference,['2026-09-26T01:13:29Z','2026-09-26T01:14:03Z']);
 assert.deepEqual(d.secondary,['2026-10-08T01:13:29Z','2026-10-08T01:14:03Z']);
 assert.equal(g.windows({product:'GOFF',name:'no_dates'}).reference,null);
});
test('single acquisition retains sub-minute start and end',()=>{
 const d=g.windows({...box('0 0 10 10')});
 assert.deepEqual(d.reference,['2026-09-01T00:00:00Z','2026-09-01T00:00:30Z']);
 assert.equal(d.pair,false);
 assert.equal(g.label('005_A_020_4005_DHDH_P05023'),'Track 005 · Ascending · Frame 020 · 4005 / DHDH · P05023');
});
test('uses the actual polygon rather than its larger bounding rectangle',()=>{
 const scene={product:'GCOV',polygons:[['0 0 0 10 10 0 0 0']]};
 const value=g.areaCoverage([scene],[0,0,10,10]);
 assert.ok(value>48&&value<52);
 assert.ok(g.coverage(g.boxes(scene),[0,0,10,10])===100);
 assert.equal(g.areaCoverage([scene,scene],[0,0,10,10]),value);
});
test('polygon spanning the dateline covers AOIs on either side',()=>{
 const scene={product:'GCOV',polygons:[['-10 170 -10 -170 10 -170 10 170 -10 170']]};
 assert.equal(g.areaCoverage([scene],[175,-5,179,5]),100);
 assert.equal(g.areaCoverage([scene],[-179,-5,-175,5]),100);
 assert.equal(g.areaCoverage([scene],[-10,-5,10,5]),0);
});
test('selection totals convert catalog decimal MB to bytes and GiB and preserve unknown sizes',()=>{
 const stats=g.selectionStats([{size_mb:1073.741824},{size_mb:0},{size_mb:null,local:true}]);
 assert.equal(stats.bytes,1024**3);assert.equal(stats.count,3);assert.equal(stats.unknown,2);assert.equal(stats.local,1);
 assert.equal(g.sizeLabel(stats),'At least 1.00 GiB');
 assert.equal(g.sizeLabel(g.selectionStats([{size_mb:NaN}])),'Size unavailable');
 assert.equal(g.selectionStats([{size_mb:9000}]).oversized,1);
});
test('selected rectangle size is geographic area rather than a proportional file-size estimate',()=>{
 assert.equal(g.rectangleKm2(null),null);
 assert.ok(Math.abs(g.rectangleKm2([0,0,1,1])-12363.7)<1);
 assert.ok(g.rectangleKm2([0,60,1,61])<g.rectangleKm2([0,0,1,1]));
});
