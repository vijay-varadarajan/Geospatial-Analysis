# Healthcare Accessibility Analysis in India 
(Inspired by Timor Leste Case Study)

## Overview

This project analyzes healthcare accessibility across India's regions, taking inspiration from a similar study conducted for Timor Leste. The study provides a visual representation of population distribution, hospitals, and areas accessible within a certain time limit around healthcare facilities. It leverages geospatial data and population datasets to identify regions with limited healthcare access and visualize results on interactive maps.

Navigate to **./Access_analysis_result_maps/** to view the results of the analysis

## Table of Contents

1. [Project Motivation](#project-motivation)
2. [Setup](#setup)
3. [Data Sources](#data-sources)
4. [Code Walkthrough](#code-walkthrough)
5. [Visualization](#visualization)
6. [Results and Insights](#results-and-insights)
7. [Future Improvements](#future-improvements)

## Project Motivation

Inspired by a case study conducted for Timor Leste, this project uses spatial and population data to evaluate healthcare accessibility. The objective is to understand the reach of healthcare facilities across specific regions, identify areas with limited access, and visualize population density and healthcare reach effectively.

## Setup

### Prerequisites

Ensure you have Python 3.x and the following libraries installed:

```bash
pip install folium pandas geopandas hdx-python-api shapely numpy matplotlib gadm
```

### API Keys

This project uses the [OpenRouteService API](https://openrouteservice.org/) to generate isochrones (areas accessible within a specified time) around hospitals. Get an API key from OpenRouteService and replace `ors_api_key` in the code.

## Data Sources

1. **Population Data**: Population data at the 1 km² resolution for India from [WorldPop](https://www.worldpop.org/).
2. **Geospatial Boundaries**: Administrative boundaries from [GADM](https://gadm.org/) using the `GADMDownloader`.
3. **Healthcare Facilities**: Hospital locations obtained through OpenStreetMap via the Overpass API.

## Code Walkthrough

### 1. Load Libraries

The following libraries are essential for data processing, mapping, and API integration:

```python
import folium as fl
import pandas as pd
import geopandas as gpd
from hdx.api.configuration import Configuration
from hdx.data.resource import Resource
import json
import itertools
from shapely.geometry import Polygon, MultiPolygon
import time
import numpy as np
from gadm import GADMDownloader
```

### 2. Load and Preprocess Population Data

The population data file (`ppp_IND_2020_1km_Aggregated_UNadj.csv`) is loaded and processed to focus on specific coordinates and their associated population counts.

```python
popdf = pd.read_csv('./ppp_IND_2020_1km_Aggregated_UNadj.csv')
popdf.columns = ['ID', 'xcoord', 'ycoord', 'population']
pop = gpd.GeoDataFrame(popdf, geometry=gpd.points_from_xy(x=popdf.xcoord, y=popdf.ycoord))
```

### 3. Retrieve Country Boundaries Using GADM

GADMDownloader provides administrative boundaries for the selected region. The code retrieves and filters boundaries for the state (`West Bengal`) and region (`Nadia`).

```python
downloader = GADMDownloader(version="4.0")
country_name = "IND"
ad_level = 2
copygdf = downloader.get_shape_data_by_country_name(country_name=country_name, ad_level=ad_level)
```

### 4. Map Population Distribution

Using `folium`, an interactive map displays the population distribution within the region. The population density is represented by the opacity and color intensity of markers based on quartile population values.

```python
quartile_labels = [0.1, 0.25, 0.5, 1.0]
population_aoi['opacity'] = pd.qcut(population_aoi['population'], 4, labels=quartile_labels)
```

### 5. Extract and Map Hospital Locations

Hospital data for the region is fetched from OpenStreetMap through the Overpass API, creating markers on the map to represent healthcare facilities within the selected area.

```python
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
```

### 6. Generate Isochrone Polygons for Hospitals

Using the OpenRouteService API, isochrone polygons are generated to show the areas accessible within a 30-minute drive from each hospital, providing insights into the regions within reach of healthcare services.

```python
def get_isochrone_osm(each_hosp):
    body = {"locations": [[each_hosp.x, each_hosp.y]], "range": [1800], "range_type": 'time'}
    response = requests.post('https://api.openrouteservice.org/v2/isochrones/driving-car', json=body, headers=headers)
    geom = json.loads(response.text)['features'][0]['geometry']
    return Polygon(geom['coordinates'][0])
```

### 7. Population Access Analysis

The project calculates the proportion of the population with hospital access by overlaying population data within the isochrones. This measure helps to determine the percentage of people who can access healthcare services within a specific travel time.

```python
def get_pop_count(cachment, pop_data):
    pop_access = pop_data[pop_data.within(cachment)]
    return pop_access['population'].sum().round()

selected_hosp['pop_with_access'] = selected_hosp['cachment_area'].apply(get_pop_count, pop_data=population_aoi)
```

## Visualization

The map includes:

- **Population Density**: Markers indicate population concentration, with color and size varying by density.
- **Hospital Locations**: Hospitals are marked, with accessible regions shaded based on the isochrone analysis.
- The region coloured green suggest good access, while the population in the region coloured red have poor access.
- **Access Legend**: A legend displays population access levels, indicating areas with high or low accessibility.

## Results and Insights

- **Population with Access**: The percentage of the population with access to healthcare is calculated, giving a quantifiable measure of healthcare reach.
- **Accessibility Disparity**: Regions with lower access are visually highlighted, providing a focus for policy or healthcare infrastructure improvements.
- **Interactive Map**: The interactive map allows users to explore population distribution, hospital locations, and accessibility areas.

<a href="./Access_analysis_result_maps/Adilabad_Telangana_access.html" target="_blank">Open Interactive Map</a>


## Future Improvements

1. **Dynamic Data Integration**: Automate data updates to reflect real-time changes in population or healthcare facilities.
2. **Addition of Health Services**: Extend the analysis recommend optimal locations to place new healthcare facilities to improve accessibility.
3. **Accessibility Scenarios**: Include different transport modes or access times (e.g., 15 minutes, 1 hour) to study varying levels of accessibility.

This project provides a foundational framework for analyzing healthcare accessibility across geographies, inspired by the Timor Leste case study but applied to India's specific regional and demographic context. The visualization and analysis approach can be adapted to other regions or services as required.

## References

[The Timor Leste case study](https://medium.com/towards-data-science/an-open-data-driven-approach-to-optimising-healthcare-facility-locations-using-python-397b3ce38185?sk=9b9ab370d93fb60929511dea42be000d)
