"""Create a source-only baseline snapshot. Never package runtime data or environments."""
import argparse,hashlib,json,re,zipfile,subprocess,sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
def file_digest(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version',default='0.9.0')
parser.add_argument('--manifest-only',action='store_true',help='Refresh source hashes without creating a release ZIP.')
parser.add_argument('--include-example-inputs',action='store_true',help='Include protected example HDF5 inputs; ordinary runtime data and credentials remain excluded.')
args=parser.parse_args()
if not re.fullmatch(r'\d+\.\d+\.\d+',args.version):parser.error('Use a semantic version such as 0.1.1.')
if (root/'scripts/stamp_assets.py').is_file():subprocess.run([sys.executable,str(root/'scripts/stamp_assets.py')],check=True)
files=[]
for name in ['README.md','.gitignore','requirements.txt','requirements-lock.txt','setup.sh','start.sh','Launch NISAR.command']:
 files.append(root/name)
for name in ['LICENSE','THIRD_PARTY_NOTICES.md','CITATION.cff']:
 if (root/name).is_file():files.append(root/name)
for directory in ['backend','frontend','scripts','tests','docs','Examples','Recipes','Validation','Demonstration']:
 for p in (root/directory).rglob('*'):
  if p.is_symlink() or not p.is_file() or any(part in {'__pycache__','.pycache','.pytest_cache','archive','ToRemove','.DS_Store'} for part in p.relative_to(root).parts):continue
  if p.suffix in {'.pyc','.pyo'} or p.name=='baseline-manifest.json':continue
  # New research and rehearsal documents travel with the README, never their
  # native inputs, private runtime or raw reference rasters.
  if directory in {'Validation','Demonstration'}:
   parts=p.relative_to(root/directory).parts
   if any(part in {'inputs','runtime','raw','arrays','jobs','workflows'} or part.startswith('runtime-') for part in parts[:-1]):continue
   if p.suffix.lower() in {'.h5','.hdf5','.tif','.tiff','.jp2','.part','.npz','.npy'}:continue
   if directory=='Demonstration' and any(part in {'Recording','Short-Presentation'} for part in parts):
    if any(part in {'audio','captures','quality','drafts','kie-media','assets','slides','render','provider'} for part in parts[:-1]):continue
    if p.name not in {'README.md','NARRATION.md','storyboard.json','storyboard-final.json','build_video.py','render_final.py','check_video.py','final-captions.srt','RECORDING_RECEIPT.json','BUDGET.json','NARRATION.txt','make_story.py','build_slides.py','render_presentation.py','check_presentation.py','captions.srt','RECEIPT.json'}:continue
  if directory=='Examples' and not args.include_example_inputs and ('inputs' in p.relative_to(root/'Examples').parts or p.name=='input-manifest.json'):continue
  files.append(p)
files=sorted(set(files))
manifest={'version':args.version,'scope':'Includes protected example inputs; excludes credentials and ordinary runtime data/environments.' if args.include_example_inputs else 'Source-only local research baseline; includes example tutorials but excludes credentials, example HDF5 inputs and runtime data/environments.','files':{str(p.relative_to(root)):file_digest(p) for p in files}}
manifest_path=root/'docs/baseline-manifest.json';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
if args.manifest_only:
 print(f'Updated source manifest: {len(files)} files; no release ZIP created.');raise SystemExit()
files.append(manifest_path)
release=root/'releases';release.mkdir(exist_ok=True)
path=release/f'nisar-observatory-{args.version}.zip'
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,Path(f'nisar-observatory-{args.version}')/p.relative_to(root))
 z.writestr(f'nisar-observatory-{args.version}/data/.gitkeep','')
digest=file_digest(path)
path.with_suffix('.zip.sha256').write_text(f'{digest}  {path.name}\n')
print(f'Created {path.name}: {len(files)} files; ordinary runtime data and credentials excluded. Protected example inputs: {args.include_example_inputs}.')
