"""Stamp local JS/CSS URLs with content hashes so releases cannot mix UI versions."""
import hashlib,re
from pathlib import Path

def stamp(root):
 front=root/'frontend';page=front/'index.html';text=page.read_text()
 def replace(match):
  prefix,url=match.groups();relative=url.split('?',1)[0]
  if not relative.startswith('/') or Path(relative).suffix not in ['.js','.css']:return match.group(0)
  asset=front/relative.lstrip('/')
  if not asset.is_file() or not asset.resolve().is_relative_to(front.resolve()):return match.group(0)
  digest=hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
  return prefix+relative+'?v='+digest+'"'
 updated=re.sub(r'((?:src|href)=")([^"\n]+)"',replace,text)
 if updated!=text:page.write_text(updated)
 return updated!=text

if __name__=='__main__':
 print('Asset URLs updated.' if stamp(Path(__file__).resolve().parents[1]) else 'Asset URLs already current.')
