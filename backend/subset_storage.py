"""Product/time folders and bounded discovery of both new and legacy extracts."""
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import PurePosixPath
from .catalog import validate_bbox

ID_PATTERN=r'subset-[a-f0-9]{32}'
FOLDER_PATTERN=r'(?:GCOV|GUNW|GOFF|SME2)_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_UTC(?:_\d+)?'

def subset_file(root,item):
 if item.get('example_id'):
  from .examples import protected_file
  return protected_file(root,item)
 if not re.fullmatch(ID_PATTERN,item['id']):raise ValueError('Invalid saved-area identity.')
 base=root/'subsets';relative=item.get('subset_path')
 if not relative:return base/(item['id']+'.h5') # Existing flat-layout extracts remain valid.
 p=PurePosixPath(relative)
 if p.is_absolute() or len(p.parts)!=2 or not re.fullmatch(FOLDER_PATTERN,p.parts[0]) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,240}\.h5',p.parts[1]) or p.parts[1].startswith('.'):
  raise ValueError('Invalid saved-area storage path.')
 target=base.joinpath(*p.parts)
 if not target.resolve().is_relative_to(base.resolve()):raise ValueError('Saved-area path is outside the data folder.')
 if not target.is_file():
  # Whole-folder moves preserve the sidecar and native filename. Resolve within
  # the managed tree without rewriting user metadata or accepting caller paths.
  for sidecar in sorted(base.rglob(item['id']+'.json')):
   moved=sidecar.parent/p.name
   if moved.resolve().is_relative_to(base.resolve()) and moved.is_file():return moved
 return target

def new_folder(root,product,stamp=None):
 if product not in ['GCOV','GUNW','GOFF','SME2']:raise ValueError('Unknown subset product.')
 base=root/'subsets';base.mkdir(parents=True,exist_ok=True)
 stamp=stamp or datetime.now(timezone.utc)
 name=f'{product}_{stamp.astimezone(timezone.utc):%Y-%m-%d_%H-%M-%S}_UTC'
 for index in range(10000):
  directory=base/(name if index==0 else f'{name}_{index+1:02}')
  try:directory.mkdir();return directory
  except FileExistsError:continue
 raise ValueError('Could not allocate a unique subset download folder.')

def filename(source_name,ident):
 stem=source_name.removesuffix('.h5')
 stem=re.sub(r'[^A-Za-z0-9_.-]','_',stem)[:200]
 return stem+'__subset_'+ident.removeprefix('subset-')[:12]+'.h5'

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()

def saved_items(root,ident=None):
 base=root/'subsets'
 if not base.exists():return
 for path in sorted(base.rglob((ident+'.json') if ident else 'subset-*.json')):
  try:
   item=json.loads(path.read_text())
   if not re.fullmatch(ID_PATTERN,item['id']) or not item.get('subset'):continue
   validate_bbox(item['subset_bbox'])
   if not subset_file(root,item).is_file():continue
   yield item
  except (ValueError,KeyError,TypeError,OSError):continue

def describe_folder(directory):
 text='''NISAR Observatory — saved area data

This folder groups one product and a download/import date and time, in UTC.
The HDF5 files contain native-grid area extracts, not complete NASA products.

To import the whole folder again:
  1. In Explore Earth, click Import subset folder and select this folder.
  2. All its HDF5 inputs are loaded together; other files are skipped.
  3. Select an analysis rectangle inside their saved area, then run a tool
     or load a compatible workflow and review its recorded settings.

For individual files, choose Import .h5 data (multiple selection is supported).
If these inputs are already saved in this app, use Use saved data instead of
importing or downloading them again.

Each new .h5 embeds its source, dates, product and saved-area bounds.
You can import it by itself; the JSON sidecar is useful for inspection and backup.
Keep the complete folder when sharing or backing up for the fullest record.

Use saved data also finds files in these product/time folders automatically.
No Earthdata password or session cookie is saved here.
'''
 (directory/'README.txt').write_text(text)
