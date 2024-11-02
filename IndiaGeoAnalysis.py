# %% [markdown]
# ### Load required libraries

# %%
import folium as fl
import pandas as pd
import geopandas as gpd
from hdx.api.configuration import Configuration
from hdx.data.resource import Resource
import json
import itertools
from shapely.geometry import Polygon,MultiPolygon
import time
import numpy as np
from gadm import GADMDownloader

# %% [markdown]
# ### Load and preprocess India's population data (2022)

# %%
popdf = pd.read_csv('./ppp_IND_2020_1km_Aggregated_UNadj.csv')

# %%
popdf = popdf.reset_index()
popdf.head()

# %%
popdf.columns = ['ID','xcoord','ycoord','population']
popdf['population'] = popdf['population'].astype(int)
pop = gpd.GeoDataFrame(popdf,geometry=gpd.points_from_xy(x=popdf.xcoord, y=popdf.ycoord))

# %%
print('Total Population:',round(pop['population'].sum()/1000000,2),'million')

# %% [markdown]
# ### Get country boundaries using GADM

# %%
# Initialize the GADMDownloader with the specified version (in this case, version 4.0)
downloader = GADMDownloader(version="4.0")

# Define the country name for which you want to retrieve administrative boundary data
country_name = "IND"

# Specify the administrative level you are interested in (e.g., 1 for districts or provinces)
ad_level = 2

# Retrieve the geospatial data for the selected country and administrative level
copygdf = downloader.get_shape_data_by_country_name(country_name=country_name, ad_level=ad_level)

# %%
copygdf

# %%
gdf = copygdf

# %% [markdown]
# ### Select required state and region

# %%
region_name, state_name = 'Nadia', 'West Bengal'

# %%
gdf['NAME_1'].unique()

# %%
gdf = gdf[gdf['NAME_1'] == state_name]

# %%
gdf['NAME_2'].unique()

# %%
gdf = gdf[gdf['NAME_2'] == region_name]

# %%
selected_gdf = gdf

# %%
from IPython.display import display, HTML

display(HTML("""
    <style>
        .map-container {
            width: 60% !important;  /* Adjust width as needed */
            height: 40% !important; /* Adjust height as needed */
            margin: 0 auto;         /* Center the map */
            border: 2px solid black; /* Optional: to visualize the map container */
        }
        .leaflet-container {
            width: 60% !important;  /* Make sure the leaflet map takes up the full width of the container */
            height: 40% !important; /* Full height within the container */
        }
    </style>
"""))

m = fl.Map(zoom_start=1, tiles="OpenStreetMap")

bounds = selected_gdf.total_bounds 

m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

for _, r in selected_gdf.iterrows():

    sim_geo = gpd.GeoSeries(r["geometry"]).simplify(tolerance=0.0001)

    geo_j = sim_geo.to_json()


    geo_j = fl.GeoJson(data=geo_j, style_function=lambda x: {"fillColor": "red"})


    fl.Popup(r["NAME_2"]).add_to(geo_j)


    geo_j.add_to(m)

display(HTML('<div class="map-container">' + m._repr_html_() + '</div>'))


# %% [markdown]
# ### Population distribution in the area of interest

# %%
pop = pop.set_crs(selected_gdf.crs)

# %%
population_aoi = gpd.sjoin(pop, selected_gdf, predicate='within')
print(f'Total Population (Area of Interest - {selected_gdf}):',round(population_aoi['population'].sum()))

# %%
quartile_labels = [0.1, 0.25, 0.5, 1.0]
population_aoi['opacity'] = pd.qcut(population_aoi['population'], 4, labels=quartile_labels)

# %%
print(population_aoi.head())

# %%
print(population_aoi.describe())

# %% [markdown]
# ### Show the population distribution in the area of interest

# %%
import folium as fl
import geopandas as gpd

m = fl.Map(zoom_start=12, tiles="OpenStreetMap")

bounds = selected_gdf.total_bounds 

m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

for _, r in selected_gdf.iterrows():

    sim_geo = gpd.GeoSeries(r["geometry"]).simplify(tolerance=0.0001)

    geo_j = sim_geo.to_json()

    geo_j = fl.GeoJson(data=geo_j, style_function=lambda x: {"fillColor": "#ffffcc", "color": "black", "weight": 2, "fillOpacity": 0.3})


    geo_j.add_to(m)

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

vmin = np.log1p(population_aoi['population'].min()+1) 
vmax = np.log1p(population_aoi['population'].max()) 

cmap = plt.get_cmap("OrRd") 
norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)

for _, row in population_aoi.iterrows():

    coords = (row['ycoord'], row['xcoord']) 

    population_value = row['population']
    if population_value > 0:
        fill_color = mcolors.rgb2hex(cmap(norm(np.log1p(population_value)))[:3]) 
    else:
        fill_color = "#ffb68700" 

    fl.CircleMarker(
        location=coords,
        radius=2*max(2, np.log1p(population_value) / 5), 
        color=fill_color,
        fill=True,
        fill_opacity=0.7,
        opacity=0.4, 
        popup=f"Population: {population_value}" 
    ).add_to(m)
    
m

# %% [markdown]
# ### Get all hospital data in the AOI using Overpass API

# %%
import requests

overpass_url = "https://overpass-api.de/api/interpreter"
overpass_query = """
[out:json];
area["ISO3166-1"="IN"]["admin_level"="2"];
(node["amenity"="hospital"](area);
 way["amenity"="hospital"](area);
 rel["amenity"="hospital"](area);
);
out center;
"""
response = requests.get(overpass_url, params={'data': overpass_query})
data = response.json()

# %%
df_hospitals = pd.DataFrame(data['elements'])

df_hospitals['name'] = df_hospitals['tags'].apply(lambda x:x['name'] if 'name' in list(x.keys()) else None)

df_hospitals = df_hospitals[['id','lat','lon','name']].drop_duplicates()

df_health_osm = df_hospitals
df_health_osm = gpd.GeoDataFrame(df_health_osm, geometry=gpd.points_from_xy(df_health_osm.lon, df_health_osm.lat))
df_health_osm = df_health_osm[['id','name','geometry']]

print('Number of hospitals extracted:',len(df_health_osm))
df_health_osm = df_health_osm.set_crs(selected_gdf.crs)

# %%
selected_hosp = gpd.sjoin(df_health_osm, selected_gdf, predicate='within')
print('Number of hospitals in AOI (',selected_gdf,'):',len(selected_hosp))

# %%
selected_hosp.head(2)

# %%

for _, row in selected_hosp.iterrows():

    coords = (row.geometry.y, row.geometry.x) 

    hospital_name = row['name'] if row['name'] else "Unnamed Hospital"

    fl.CircleMarker(
        location=coords,
        radius=3, 
        color='black',
        fill=True,
        fill_color='black',
        fill_opacity=0.7,
        popup=hospital_name
    ).add_to(m)

m

# %% [markdown]
# ### Get isochrone polygons using ORS API and calculate percentage of population access

# %%
ors_api_key = 'ORS_API_KEY_HERE'

# %%
def get_isochrone_osm (each_hosp):
  body = {"locations":[[each_hosp.x,each_hosp.y]],"range":[1800],"range_type":'time'}
  headers = {
      'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
      'Authorization': ors_api_key,
      'Content-Type': 'application/json; charset=utf-8'
  }
  call = requests.post('https://api.openrouteservice.org/v2/isochrones/driving-car', json=body, headers=headers)
  print(call.text)
  geom = (json.loads(call.text)['features'][0]['geometry'])
  polygon_geom = Polygon(geom['coordinates'][0])
  time.sleep(3)
  return polygon_geom

selected_hosp['cachment_area'] = selected_hosp['geometry'].apply(get_isochrone_osm)

# %%
def get_pop_count(cachment,pop_data):
  pop_access = pop_data[pop_data.within(cachment)]
  id_values = (pop_access['ID'].values)
  pop_with_access = (pop_access['population'].sum().round())
  return id_values,pop_with_access

selected_hosp['id_with_access'], selected_hosp['pop_with_access'] = zip(*selected_hosp['cachment_area'].apply(get_pop_count, pop_data=population_aoi))

# %%
list_ids_access = list(selected_hosp['id_with_access'].values)
list_ids_access = list(itertools.chain.from_iterable(list_ids_access))
pop_with_access = population_aoi[population_aoi['ID'].isin(list_ids_access)]
pop_without_access = population_aoi[~population_aoi['ID'].isin(list_ids_access)]

print('Population with Access:',round(pop_with_access['population'].sum()*100/population_aoi['population'].sum(),2),'%')

# %%
from IPython.display import display, HTML
import folium as fl


display(HTML("""
    <style>
        .map-container {
            width: 60% !important;  /* Adjust width as needed */
            height: 40% !important; /* Adjust height as needed */
            margin: 0 auto;         /* Center the map */
            border: 2px solid black; /* Optional: to visualize the map container */
        }
        .leaflet-container {
            width: 100% !important;  /* Make sure the leaflet map takes up the full width of the container */
            height: 100% !important; /* Full height within the container */
        }
    </style>
"""))


folium_map = fl.Map(zoom_start=1, tiles="OpenStreetMap")


bounds = selected_gdf.total_bounds  # Returns [minx, miny, maxx, maxy]


folium_map.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])


folium_map.get_root().html.add_child(fl.Element(f'<h3 style="text-align:center;"><b>Healthcare access distribution</b></h3>'))
folium_map.get_root().html.add_child(fl.Element(f'<h3 style="text-align:center;"><b>{region_name, state_name}</b></h3>'))


legend_html = """
<div style="position: fixed; 
            bottom: 50px; right: 50px; 
            background-color: white; 
            padding: 20px;
            border:2px solid grey;
            z-index:9999;">
    <b>Legend</b><br>
    <i style="color:red;font-size:20px;">&#9679;</i> Population with less access<br>
    <i style="color:green;font-size:20px;">&#9679;</i> Population with high access
</div>
"""
folium_map.get_root().html.add_child(fl.Element(legend_html))

geo_adm = fl.GeoJson(data=selected_gdf.iloc[0]['geometry'],style_function=lambda x:{'color': 'orange'})
geo_adm.add_to(folium_map)

for i in range(0,len(selected_hosp)):
    fl.Marker([selected_hosp.iloc[i]['geometry'].y, selected_hosp.iloc[i]['geometry'].x],
              popup=selected_hosp.iloc[i]['name']).add_to(folium_map)

# This loop is not necessary if pop_without_access is empty
for i in range(0,len(pop_without_access)):
  fl.CircleMarker(
        location=[pop_without_access.iloc[i]['ycoord'], pop_without_access.iloc[i]['xcoord']],
        radius=3,
        color=None,
        fill=True,
        fill_color='red',
        fill_opacity=pop_without_access.iloc[i]['opacity']).add_to(folium_map)

for i in range(0,len(pop_with_access)):
  fl.CircleMarker(
        location=[pop_with_access.iloc[i]['ycoord'], pop_with_access.iloc[i]['xcoord']],
        radius=3,
        color=None,
        fill=True,
        fill_color='green',
        fill_opacity=pop_with_access.iloc[i]['opacity']).add_to(folium_map)

folium_map

# %%
folium_map.save(f'{region_name}_{state_name}_access.html')

# %%



