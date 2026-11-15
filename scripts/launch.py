"""Double-click launcher; always use the project interpreter, wait for readiness."""
import subprocess,sys,time,webbrowser,urllib.request,json
from pathlib import Path
from stamp_assets import stamp
root=Path(__file__).resolve().parents[1];stamp(root);url='http://127.0.0.1:8765'
def ready():
 try:
  with urllib.request.urlopen(url+'/api/health',timeout=1) as r:return json.load(r).get('runtime')=='project .venv'
 except Exception:return False
if ready():webbrowser.open(url);raise SystemExit()
process=subprocess.Popen([str(root/'.venv/bin/python'),'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8765','--no-access-log'],cwd=root)
try:
 for _ in range(60):
  if ready():webbrowser.open(url);break
  if process.poll() is not None:raise SystemExit('The server could not start. Check the terminal message.')
  time.sleep(.25)
 else:raise SystemExit('The server did not become ready. Check the terminal message.')
 print('NISAR Observatory is running. Keep this window open. Press Control-C to stop.')
 process.wait()
except KeyboardInterrupt:
 process.terminate();process.wait()
