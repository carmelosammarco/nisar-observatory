"""Scientific comparison figure; source pixels are not altered or georeferenced."""
from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom,reproject,Resampling
from rasterio.transform import from_bounds
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image
HERE=Path(__file__).parent;ROOT=HERE.parents[2]
bbox=[77.36,32.39,77.57,32.56]
geo=json.loads((HERE/'sources/samudra-tapu-rgi6.geojson').read_text())['features'][0]['geometry']
stops=json.loads((ROOT/'backend/mexico_palette.json').read_text())
cmap=LinearSegmentedColormap.from_list('App Rainbow',np.array(stops)/255);cmap.set_bad('#e1e7e2')
fig=plt.figure(figsize=(15,12),facecolor='#f6f7f0');gs=fig.add_gridspec(2,3,height_ratios=[.94,1],hspace=.28,wspace=.22)
source=fig.add_subplot(gs[0,:2]);img=np.array(Image.open(ROOT/'Examples/P07_Samudra_Tapu/figures/iirs-published-glacier-maps.png'))
source.imshow(img);source.set_ylim(229,0);source.axis('off');source.set_title('Published maps: NISAR and ITS_LIVE reported glacier speed',loc='left',fontsize=13,fontweight='bold',pad=10)
text=fig.add_subplot(gs[0,2]);text.axis('off');text.text(0,.98,'Different quantities\nneed different interpretations',va='top',fontsize=15,fontweight='bold',color='#173f3e')
text.text(0,.78,'Publication: 5.7–139.19 m/year (NISAR)\n0.7–132.53 m/year (ITS_LIVE).\nExact pair IDs / conversion not supplied.\n\nOur maps below: radar-plane norms,\nnot geographic horizontal speed.\nSame display endpoints do not make\nthe measurements equivalent.\n\nJanuary 1–13, 2026 · ascending track 055\nSNR ≥ 5 · 80 m analysis grid\nHistorical RGI6 glacier outline (2002)\nNo stable-terrain correction.',va='top',fontsize=11,linespacing=1.5,color='#294e4b')
labels=[('layer1-snr-only','Layer 1 · SNR screening only'),('layer3-snr-only','Layer 3 · SNR screening only'),('layer3-filtered','Layer 3 · plus spatial filter')]
for col,(folder,title) in enumerate(labels):
 ax=fig.add_subplot(gs[1,col]);ax.set_facecolor('#e1e7e2')
 with rasterio.open(HERE/'results'/folder/'radar_filtered_1.tif') as ds:
  a=ds.read(1);mask=geometry_mask([transform_geom('EPSG:4326',ds.crs,geo)],out_shape=a.shape,transform=ds.transform,invert=True)
  a[~mask]=np.nan;out=np.full((450,460),np.nan,'float32');tr=from_bounds(*bbox,460,450)
  reproject(a,out,src_transform=ds.transform,src_crs=ds.crs,src_nodata=np.nan,dst_transform=tr,dst_crs=4326,dst_nodata=np.nan,resampling=Resampling.nearest)
 im=ax.imshow(out,extent=[bbox[0],bbox[2],bbox[1],bbox[3]],origin='upper',cmap=cmap,vmin=0,vmax=140,aspect=1/np.cos(np.radians(32.48)))
 from shapely.geometry import shape
 for polygon in ([shape(geo)] if shape(geo).geom_type=='Polygon' else shape(geo).geoms):
  x,y=polygon.exterior.xy;ax.plot(x,y,color='#294e4b',linewidth=.55)
 ax.set_xlim(77.37,77.54);ax.set_ylim(32.395,32.545);ax.set_title(title,fontsize=12,fontweight='bold',color='#173f3e');ax.set_xlabel('Longitude · °E');ax.set_ylabel('Latitude · °N');ax.ticklabel_format(useOffset=False);ax.tick_params(labelsize=9)

cbax=fig.add_axes([.29,.125,.42,.016]);cb=fig.colorbar(im,cax=cbax,orientation='horizontal',extend='max');cb.set_label('Radar-plane magnitude · annualized m/year · same scale for all three app maps',fontsize=10)
fig.suptitle('Samudra Tapu | Real NISAR offsets, with a critical comparison',fontsize=21,fontweight='bold',color='#173f3e',x=.07,ha='left',y=.97)
fig.text(.07,.035,'Gray = outside the historical glacier outline or no usable measurements. Values above 140 retain their numeric values but saturate in this figure.\nThe spatial filter removes concentrated motion as well as outliers. These results do not reproduce or validate the published horizontal-speed map.\nSource figure: Malviya, Garg & Thakur (IIRS, 2026), DOI 10.65456/iirs.2026.10.3.1. Original source image preserved in the Samudra Tapu example.',fontsize=10,color='#355a54',linespacing=1.6)
fig.subplots_adjust(top=.91,bottom=.22,left=.07,right=.96)
fig.savefig(HERE/'figures/samudra-tapu-comparison.png',dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
