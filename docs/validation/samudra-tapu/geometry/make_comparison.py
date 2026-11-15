from pathlib import Path
import json
import numpy as np,rasterio
from rasterio.warp import reproject,Resampling
from rasterio.transform import from_bounds
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image
from shapely.geometry import shape
HERE=Path(__file__).parent;ROOT=HERE.parents[3];bbox=[77.36,32.39,77.57,32.56]
geo=shape(json.loads((HERE.parent/'sources/study-domain.geojson').read_text())['features'][0]['geometry'])
cmap=LinearSegmentedColormap.from_list('App Rainbow',np.array(json.loads((ROOT/'backend/mexico_palette.json').read_text()))/255);cmap.set_bad('#e2e8e1')
fig=plt.figure(figsize=(16,11),facecolor='#f7f8f1');gs=fig.add_gridspec(2,3,height_ratios=[.8,1.2],hspace=.32,wspace=.24)
ax=fig.add_subplot(gs[0,:2]);img=np.array(Image.open(HERE.parent/'sources/iirs-samudra-bara-shigri.png'));ax.imshow(img);ax.set_ylim(229,0);ax.axis('off');ax.set_title('Published Samudra Tapu maps · NISAR (left) and ITS_LIVE (right)',loc='left',fontsize=12,fontweight='bold')
ax=fig.add_subplot(gs[0,2]);ax.axis('off');ax.text(0,1,'A closer quantity,\nwith explicit assumptions',va='top',fontsize=16,fontweight='bold',color='#163f3d');ax.text(0,.71,'Publication NISAR: 5.7–139.19 m/year\nPublication ITS_LIVE: 0.7–132.53 m/year\n\nOur January 1–13 estimate:\n0.84–144.94 m/year · median 21.79\n53.62% of historical outline mapped\n\nZero vertical velocity; 5,000 m geometry height.\nNo spatial filter or stable-ground subtraction.\nExact published pair and conversion unknown.',va='top',fontsize=10.5,linespacing=1.45,color='#355650')
for col,(name,title,label,limits,colour) in enumerate([
 ('radar_magnitude','Earlier quantity · radar-plane magnitude','Annualized m/year · not horizontal speed',(0,140),cmap),
 ('horizontal_speed','New estimate · horizontal speed','Annualized m/year · vertical velocity = 0',(0,140),cmap),
 ('horizontal_vertical_sensitivity_0','Sensitivity · unmeasured vertical motion','Horizontal-vector bias for |vUp| = 20 m/year',(0,30),'magma')]):
 ax=fig.add_subplot(gs[1,col]);ax.set_facecolor('#e2e8e1')
 with rasterio.open(HERE/'results/january'/f'{name}.tif') as ds:
  a=ds.read(1);out=np.full((500,500),np.nan,'float32');tr=from_bounds(*bbox,500,500)
  reproject(a,out,src_transform=ds.transform,src_crs=ds.crs,src_nodata=np.nan,dst_transform=tr,dst_crs=4326,dst_nodata=np.nan,resampling=Resampling.nearest)
 im=ax.imshow(out,extent=[bbox[0],bbox[2],bbox[1],bbox[3]],origin='upper',cmap=colour,vmin=limits[0],vmax=limits[1],aspect=1/np.cos(np.radians(32.48)))
 for polygon in ([geo] if geo.geom_type=='Polygon' else geo.geoms):
  x,y=polygon.exterior.xy;ax.plot(x,y,color='#36594f',linewidth=.55)
 ax.set_xlim(77.37,77.54);ax.set_ylim(32.395,32.545);ax.set_title(title,fontsize=12,fontweight='bold',color='#163f3d');ax.set_xlabel('Longitude · °E');ax.set_ylabel('Latitude · °N');ax.ticklabel_format(useOffset=False);ax.tick_params(labelsize=9)
 cb=fig.colorbar(im,ax=ax,orientation='horizontal',pad=.13,fraction=.045,extend='max' if col<2 else 'neither');cb.set_label(label,fontsize=9)
fig.suptitle('Samudra Tapu | From radar offsets to conditional horizontal speed',x=.065,y=.97,ha='left',fontsize=20,fontweight='bold',color='#163f3d')
fig.text(.065,.025,'Same native offsets, layer 3 and SNR ≥ 5. Gray = outside the historical RGI6 outline (2002) or no usable measurements.\nThe 20 m/year vertical scenario is an assumption sensitivity, not a confidence interval. Range similarity is not pixelwise validation.\nSource figure: Malviya, Garg & Thakur, IIRS (2026), DOI 10.65456/iirs.2026.10.3.1. Original figure preserved; upper Samudra row shown.',fontsize=10,color='#355650',linespacing=1.5)
fig.subplots_adjust(top=.90,bottom=.15,left=.065,right=.97)
fig.savefig(HERE/'samudra-horizontal-comparison.png',dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
