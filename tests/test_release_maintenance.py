"""Portable release contents and verification after ordinary run cleanup."""
import hashlib,importlib.util,json,shutil,subprocess,sys,zipfile
from pathlib import Path
import numpy as np
import pytest
import rasterio
from backend.app import APP_VERSION
from rasterio.transform import from_origin
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('include_inputs',[False,True])
def test_source_release_keeps_recipes_and_excludes_personal_data(tmp_path,include_inputs):
 script=tmp_path/'scripts/package_release.py';script.parent.mkdir();shutil.copy(ROOT/'scripts/package_release.py',script)
 for name in ['README.md','.gitignore','requirements.txt','requirements-lock.txt','setup.sh','start.sh','Launch NISAR.command','backend/app.py','frontend/index.html','frontend/assets/media/nisar-observatory-introduction.mp4','frontend/ToRemove/private.json','ToRemove/2026-10-23/data/private.h5','tests/sample.py','docs/guide.md','Recipes/example.json','Examples/case/README.md','Examples/case/inputs/source.h5','Examples/case/input-manifest.json','data/workflows/private.json','data/raw/private.h5','archive/old.txt','docs/archive/old.txt','backend/__pycache__/old.pyc','.env','docs/.pytest_cache/cache','Demonstration/2026/SCRIPT.md','Demonstration/2026/runtime/jobs/private.json','Validation/Transfer_2026/DOWNLOAD_PROPOSAL.md','Validation/Transfer_2026/Lucas/inputs/source.h5','Validation/Transfer_2026/Lucas/references/optical/raw.tif','Validation/Transfer_2026/Lucas/comparison-arrays.npz','Validation/Transfer_2026/Lucas/temporary.npy','Demonstration/2026/Recording/README.md','Demonstration/2026/Recording/NISAR-Observatory-demonstration.mp4','Demonstration/2026/Recording/audio/private.wav','Demonstration/2026/Recording/captures/screen.png','Demonstration/2026/Short-Presentation/README.md','Demonstration/2026/Short-Presentation/film.mp4','Demonstration/2026/Short-Presentation/provider/media/voice.wav','Demonstration/2026/Short-Presentation/captures/screen.png']:
  p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture')
 args=[sys.executable,str(script)]
 if include_inputs:args.append('--include-example-inputs')
 subprocess.run(args,check=True,capture_output=True)
 package=tmp_path/f'releases/nisar-observatory-{APP_VERSION}.zip'
 with zipfile.ZipFile(package) as archive:
  names=[p.removeprefix(f'nisar-observatory-{APP_VERSION}/') for p in archive.namelist()]
  assert 'Recipes/example.json' in names and 'Examples/case/README.md' in names
  assert 'Demonstration/2026/SCRIPT.md' in names and 'Validation/Transfer_2026/DOWNLOAD_PROPOSAL.md' in names
  assert 'Demonstration/2026/Recording/README.md' in names
  assert 'Demonstration/2026/Short-Presentation/README.md' in names
  assert 'frontend/assets/media/nisar-observatory-introduction.mp4' in names
  assert not any((p.startswith('Demonstration/') and p.endswith(('.mp4','.wav'))) or '/Recording/captures/' in p or '/Short-Presentation/captures/' in p or '/ToRemove/' in p or p.startswith('ToRemove/') for p in names)
  assert not any(p.startswith('Validation/') and p.endswith(('.h5','.tif','.npz','.npy')) for p in names)
  assert ('Examples/case/inputs/source.h5' in names)==include_inputs
  assert ('Examples/case/input-manifest.json' in names)==include_inputs
  assert not any('private' in p or 'archive/' in p or '__pycache__' in p or '.pytest_cache' in p or p=='.env' for p in names)
  manifest=json.loads(archive.read(f'nisar-observatory-{APP_VERSION}/docs/baseline-manifest.json'))
  for name,digest in manifest['files'].items():assert hashlib.sha256(archive.read(f'nisar-observatory-{APP_VERSION}/'+name)).hexdigest()==digest

def verifier():
 spec=importlib.util.spec_from_file_location('protected_replay',ROOT/'scripts/verify_example_workflows.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def test_cleared_historical_run_does_not_break_direct_example_verification(tmp_path):
 m=verifier();result=m.compare_saved_browser(tmp_path,{'raster':'/api/artifacts/'+'a'*32+'/LAB/summary.tif'},{'rate':'summary'},{'rate':'unused'})
 assert 'not available' in result['browser_export_check'] and 'browser_numeric_maps_identical' not in result

def test_partial_and_changed_historical_exports_still_fail(tmp_path):
 m=verifier();folder=tmp_path/'data/jobs'/('a'*32)/'LAB';folder.mkdir(parents=True);a=np.ones((3,3),dtype='float32')
 with rasterio.open(folder/'summary.tif','w',driver='GTiff',width=3,height=3,count=1,dtype='float32',crs='EPSG:4326',transform=from_origin(1,2,.1,.1),nodata=np.nan) as target:target.write(a,1)
 browser={'raster':'/api/artifacts/'+'a'*32+'/LAB/summary.tif'}
 with pytest.raises(ValueError,match='incomplete'):m.compare_saved_browser(tmp_path,browser,{'rate':'summary','residual':'residual'},{})
 with pytest.raises(ValueError,match='differs'):m.compare_saved_browser(tmp_path,browser,{'rate':'summary'},{'rate':'not-matching'})
 assert m.compare_saved_browser(tmp_path,browser,{'rate':'summary'},{'rate':m.digest(a)})['browser_numeric_maps_identical']==1


def test_manifest_only_does_not_allocate_a_release_bundle(tmp_path):
 script=tmp_path/'scripts/package_release.py';script.parent.mkdir();shutil.copy(ROOT/'scripts/package_release.py',script)
 for name in ['README.md','.gitignore','requirements.txt','requirements-lock.txt','setup.sh','start.sh','Launch NISAR.command']:(tmp_path/name).write_text('fixture')
 (tmp_path/'docs').mkdir()
 subprocess.run([sys.executable,str(script),'--manifest-only'],check=True,capture_output=True)
 manifest=json.loads((tmp_path/'docs/baseline-manifest.json').read_text())
 assert manifest['version']==APP_VERSION and manifest['files']['README.md']==hashlib.sha256(b'fixture').hexdigest()
 assert not (tmp_path/'releases').exists()

def test_direct_protected_replay_refuses_a_runtime_owned_by_the_app(tmp_path):
 import os
 from backend.runtime_storage import RuntimeLease
 with RuntimeLease(tmp_path):
  result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/verify_example_workflows.py'),'--case','P01_Mozambique'],env={**os.environ,'NISAR_DATA_DIR':str(tmp_path)},cwd=ROOT,capture_output=True,text=True,timeout=15)
 assert result.returncode!=0 and 'Another server owns this runtime folder' in result.stderr
 assert not (tmp_path/'arrays').exists()
