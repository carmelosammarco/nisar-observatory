"""Replay all examples and independently re-evaluate Timber against archived vectors.

No new source downloads, no live runtime mutation and no change to science settings.
The fresh evaluation uses finite radar candidate/score support. The historical
receipt used common radar/optical support; these denominators are NOT interchangeable.
"""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
from verify_release import ROOT,verify


def boundary_comparison(folder):
 import numpy as np,rasterio
 from rasterio.features import geometry_mask
 from rasterio.warp import transform_geom
 from scipy.stats import rankdata
 with rasterio.open(folder/'fire_candidate.tif') as src:
  candidate=src.read(1);transform=src.transform;crs=src.crs;cell_ha=abs(transform.a*transform.e-transform.b*transform.d)/10000
 with rasterio.open(folder/'fire_score.tif') as src:score=src.read(1)
 valid=np.isfinite(score)&np.isfinite(candidate);positive=candidate==1
 references=ROOT/'Examples/P03_Timber_Fire/references';output={}
 for key,name in [('official_perimeter','nifc-current-perimeter.geojson'),('author_output','published-polygons.geojson')]:
  path=references/name;geo=json.loads(path.read_text())
  shapes=[transform_geom('EPSG:4326',crs,f['geometry']) for f in geo['features']]
  reference=geometry_mask(shapes,out_shape=score.shape,transform=transform,invert=True)
  tp=int((valid&reference&positive).sum());fp=int((valid&~reference&positive).sum());fn=int((valid&reference&~positive).sum());tn=int((valid&~reference&~positive).sum())
  labels=reference[valid];ranks=rankdata(score[valid],method='average');n1=int(labels.sum());n0=int((~labels).sum())
  auc=float((ranks[labels].sum()-n1*(n1+1)/2)/(n1*n0))
  output[key]={'tp':tp,'fp':fp,'fn':fn,'tn':tn,'precision':tp/(tp+fp),'recall':tp/(tp+fn),'f1':2*tp/(2*tp+fp+fn),'iou':tp/(tp+fp+fn),'auc':auc,'mapped_ha':(tp+fp)*cell_ha,'reference_ha':(tp+fn)*cell_ha,'valid_ha':int(valid.sum())*cell_ha,'reference_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 return {'protocol':'All common finite fire_score/fire_candidate radar cells; archived vectors rasterized by cell centre on the actual exported grid. AUC independently computed by average-rank Mann–Whitney statistic, including ties.','historical_protocol':'Earlier published app statistics use common radar/optical support; the optical pixel support is not bundled as a numerical mask, so its AUC is not presented as freshly recomputed.','reference_independence':{'official_perimeter':'External operational incident boundary, a proxy that can contain unburned islands; not field-level burn truth.','author_output':'Author-derived result using the same NISAR observations; agreement measures reproduction rather than independent accuracy.'},'comparisons':output}


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--keep-runtime',action='store_true',help='Retain only this isolated test runtime for browser review; never uses personal data.');args=parser.parse_args()
 runtime=Path(tempfile.mkdtemp(prefix='nisar-evidence-review-'));success=False;assessments={}
 def review(case,row,root):
  result=row['result'];assert result['reading_guide']['method']==row['pid']
  if case=='P03_Timber_Fire':assessments[case]=boundary_comparison(root/'jobs'/row['job']/row['pid'])
 try:
  replay=verify(runtime,case_review=review)
  path=ROOT/'docs/validation/example-evidence-review.json'
  path.write_text(json.dumps({'status':'PASS','review_date':'2026-10-23','scope':__doc__.strip(),'replay':replay,'boundary_evaluation':assessments},indent=2)+'\n')
  print(json.dumps({'status':'PASS','exact_original_maps':replay['exact_original_map_comparisons'],'previews':replay['saved_map_previews_checked'],'boundary_evaluation':assessments}),flush=True);success=True
 finally:
  if success and not args.keep_runtime:shutil.rmtree(runtime)
  elif success:print('Browser-review runtime retained at '+str(runtime),flush=True)
  else:print('Failure evidence retained at',runtime,flush=True)


if __name__=='__main__':main()
