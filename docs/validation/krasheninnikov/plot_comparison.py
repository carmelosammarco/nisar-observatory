from pathlib import Path
import json,numpy as np,rasterio
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
R=Path(__file__).resolve().parent;O=R/'results';F=R/'figures'
raw=[]
for k in range(5):
 with rasterio.open(O/f'evolving/observation_{k}.tif') as ds:raw.append(ds.read(1))
lo,hi=map(float,np.percentile(np.concatenate([a[np.isfinite(a)] for a in raw]),[2,98]));(O/'brightness-display.json').write_text(json.dumps({'pooled_percentiles':[2,98],'low_db':lo,'high_db':hi,'meaning':'One fixed display range shared across the five HH acquisitions; numeric rasters unchanged.'},indent=2))
dates=['18 Jun','30 Jun','12 Jul','24 Jul','17 Aug'];frames=[29,30,31,32,33]
fig,axes=plt.subplots(2,5,figsize=(20,8),layout='constrained')
for k,(date,n) in enumerate(zip(dates,frames)):
 axes[0,k].imshow(Image.open(R/f'sources/reference-frames/frame-{n:03}.jpg'));axes[0,k].axis('off');axes[0,k].set_title(f'NASA · {date} 2026',fontsize=12)
 with rasterio.open(O/f'evolving/observation_{k}.tif') as ds:
  a=ds.read(1);extent=[ds.bounds.left/1000,ds.bounds.right/1000,ds.bounds.bottom/1000,ds.bounds.top/1000]
 im=axes[1,k].imshow(a,cmap='inferno',vmin=lo,vmax=hi,extent=extent,interpolation='nearest');axes[1,k].set_aspect('equal');axes[1,k].tick_params(labelsize=8);axes[1,k].set_title(f'Our GCOV HH · {date}',fontsize=12);axes[1,k].set_xlabel('UTM easting · km')
axes[1,0].set_ylabel('UTM northing · km');fig.colorbar(im,ax=list(axes[1,:]),label=f'Gamma-zero · dB · shared {lo:.1f} to {hi:.1f}',shrink=.7)
fig.suptitle('Krasheninnikov: matching acquisition dates, different presentations',fontsize=19)
fig.supxlabel('Top: NASA/JPL-Caltech/ISRO visualization, oblique 3D, published color styling. Bottom: downloaded GCOV HH, north-up metric map. No pixelwise accuracy claim.',fontsize=11)
fig.savefig(F/'nasa-vs-gcov-five-dates.png',dpi=150);plt.close(fig)
fig,axes=plt.subplots(1,4,figsize=(17,6),layout='constrained');keys=[('evolving','latest_departure','Latest smoothed departure · dB'),('previous','surface','Previous: changed on EVERY later date'),('evolving','surface','Latest qualifying changed patches'),('evolving','confirmed_change','Latest same-sign change on ≥2 dates')]
for ax,(folder,key,title) in zip(axes,keys):
 with rasterio.open(O/f'{folder}/{key}.tif') as ds:a=ds.read(1)
 im=ax.imshow(a,cmap='RdBu_r' if key=='latest_departure' else 'cividis',vmin=-8 if key=='latest_departure' else 0,vmax=8 if key=='latest_departure' else 1,extent=extent,interpolation='nearest');ax.set_title(title,fontsize=11);ax.set_xlabel('UTM easting · km');fig.colorbar(im,ax=ax,shrink=.55)
axes[0].set_ylabel('UTM northing · km');fig.suptitle('18 June → 17 August 2026 · same 20 m grid · 3 dB rule · latest ≠ repeated',fontsize=17);fig.supxlabel('Candidate radar-scattering changes, not validated lava boundaries. Latest/repeated maps: 40 m smoothing sigma and minimum 3 ha signed patches; previous method is unsmoothed.',fontsize=10);fig.savefig(F/'processing-comparison.png',dpi=150);plt.close(fig)
print('Comparison figures saved')

# Detail panels help compare morphology without pretending the oblique image is georeferenced.
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
zoom=[160.235,54.575,160.365,54.660]
fig,axes=plt.subplots(2,3,figsize=(15,10),layout='constrained')
for ax,n,date in [(axes[0,0],29,'18 June'),(axes[0,1],33,'17 August')]:
 ax.imshow(Image.open(R/f'sources/reference-frames/frame-{n:03}.jpg'));ax.axis('off');ax.set_title('NASA · '+date+' · oblique view')
axes[0,2].axis('off');axes[0,2].text(.02,.9,'What can be compared?',fontsize=17,weight='bold');axes[0,2].text(.02,.79,'Crater geometry and bright flow structures.\n\nWhat cannot be claimed?\nPixelwise agreement, lava-area accuracy,\nor identical processing/viewing geometry.\n\nBelow: north-up detail window;\nnot an exact NASA camera footprint.\nBrightness is not temperature.\nA June baseline already includes old lava.',fontsize=13,va='top',linespacing=1.5)
for ax,key,title in zip(axes[1],['observation_0','observation_4','latest_departure'],['Our HH · 18 June','Our HH · 17 August','Our smoothed change · June → August']):
 with rasterio.open(O/f'evolving/{key}.tif') as ds:
  bounds=transform_bounds('EPSG:4326',ds.crs,*zoom,densify_pts=21);window=from_bounds(*bounds,ds.transform).round_offsets().round_lengths();a=ds.read(1,window=window);t=ds.window_transform(window);b=rasterio.transform.array_bounds(*a.shape,t);extent2=[b[0]/1000,b[2]/1000,b[1]/1000,b[3]/1000]
 change=key=='latest_departure';im=ax.imshow(a,extent=extent2,cmap='RdBu_r' if change else 'inferno',vmin=-8 if change else lo,vmax=8 if change else hi,interpolation='nearest');ax.set_title(title);ax.set_xlabel('UTM easting · km');ax.set_ylabel('UTM northing · km');fig.colorbar(im,ax=ax,shrink=.65,label='Change · dB' if change else 'Gamma-zero · dB')
fig.suptitle('Krasheninnikov · crater and eastern-flow detail',fontsize=20);fig.supxlabel('NASA/SVS reference imagery above; real downloaded GCOV below. Wider environmental changes are retained in the full-window maps, not assigned to lava.',fontsize=11);fig.savefig(F/'crater-flow-detail.png',dpi=150);plt.close(fig)
