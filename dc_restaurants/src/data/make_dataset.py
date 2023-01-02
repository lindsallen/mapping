'''Processes two external datasets and saves to interim folder
    Dataset #1 - DC licenses, limits licenses to restaurants and encodes Zillow neighborhood
    Dataset #2 - Calculates area of Zillow neighborhoods
   See notebook 1.0-lra-initial-data-exploration for cleaning assumptions
'''
import pandas as pd
import os
import json
import pyproj
from shapely.geometry import shape, Point
from shapely.ops import transform
from functools import partial
import time

__author__ = "Lindsay Allen"
__version__ = "1.0.1"
__maintainer__ = "Lindsay Allen"
__status__ = "Development"

##################################################################################
###                                     Import Data                       ########
##################################################################################

start_time = time.time()

os.chdir('..')
os.chdir('..')

#Load DC Zillow Neighborhood GeoJSON file
with open('data\\external\\zillow_nb_dc.geojson', 'r') as jsonFile:
    dc_zil_nbhd = json.load(jsonFile)    

#Load DC business license data
dc_biz = pd.read_csv("data\\external\\Basic_Business_Licenses.csv", low_memory = False)

##################################################################################
### Dataset 1 - Part A Limit DC license data to restaurants 
##################################################################################

#limit that dataset to restaurants
dc_food = dc_biz[dc_biz['LICENSE_CATEGORY_TEXT'] == 'Public Health Food Establish'].copy()

# Add license end yr, start yr, and estimate of license length to df
dc_food['LICENSE_END_YR'] = dc_food['LICENSE_END_DATE'].str.slice(start = 0,stop = 4).fillna(0).astype(int)
dc_food['LICENSE_START_YR'] = dc_food['LICENSE_START_DATE'].str.slice(start = 0,stop = 4).fillna(0).astype(int)
dc_food['LICENSE_LENGTH'] = dc_food['LICENSE_END_YR'] - dc_food['LICENSE_START_YR']

# Only retaining restaurants with a license that ended on or after 2005
dc_food = dc_food[dc_food['LICENSE_END_YR'] >= 2005]

## These are the only fields that will be used in analysis
## Limiting the dataset to these fields to ensure that duplicates caused in other columns do not skew results
cols = ['SITE_ADDRESS','ENTITY_NAME'
        ,'LICENSE_ISSUE_DATE','LICENSE_START_DATE','LICENSE_END_DATE'
        ,'LICENSECATEGORY','LICENSESTATUS'
        , 'LATITUDE', 'LONGITUDE'
        , 'WARD','ANC','SMD','DISTRICT','PSA','NEIGHBORHOODCLUSTER',
        'BUSINESSIMPROVEMENTDISTRICT','MAINSTREET','LICENSE_END_YR','LICENSE_START_YR','LICENSE_LENGTH']

dc_food = dc_food[cols]
## rounding lat and long to 6 decimals
dc_food['LATITUDE'] = dc_food['LATITUDE'].round(decimals = 6)
dc_food['LONGITUDE'] = dc_food['LONGITUDE'].round(decimals = 6)

dc_food_final = dc_food.drop_duplicates()
dc_food_final = dc_food_final[dc_food_final['LONGITUDE'].notna()]

##################################################################################
### Dataset 1 - Part B Encode neighborhood on each DC restaurant
##################################################################################

#create column that we will populate with neigbhorhood
dc_food_final['neighborhood'] = ''

long = dc_food_final.columns.get_loc('LONGITUDE')
lat = dc_food_final.columns.get_loc('LATITUDE')

## use shapely to check if lat/lon is within the zillow neighborhood shape
for i in range(len(dc_food_final)):
    point = Point(dc_food_final.iloc[i,long],dc_food_final.iloc[i,lat]) ## Longitude, Latitude

    for feature in dc_zil_nbhd['features']:
        polygon = shape(feature['geometry'])
        if polygon.contains(point):
            dc_food_final.iloc[i, dc_food_final.columns.get_loc('neighborhood')] = feature['properties']['name']

dc_food_final.to_csv("data\\interim\\DC_FoodEstablish_Since2005.csv", index = False) ## write the data so we don't have to re-run this every time

##################################################################################
### Dataset 2 - Calculate Area #####
### Note: init function is deprecated
##################################################################################

neighb_areas = dict()

for feature in dc_zil_nbhd['features']:
    geom = feature['geometry']
    name = feature['properties']['name']
    
    s = shape(geom)
    proj = partial(pyproj.transform, pyproj.Proj(init='epsg:4326'),
               pyproj.Proj(init='epsg:3857'))

    s_new = transform(proj, s)

    projected_area = transform(proj, s).area
    neighb_areas[name] = projected_area / 2589988.1103

neighb_area = pd.DataFrame.from_dict(neighb_areas, orient = 'index')

neighb_area.reset_index(level=0, inplace=True)
neighb_area.rename(columns={"index": "name", 0: "sq_mi"}, inplace = True)
neighb_area.to_csv("data\\interim\\neigbh_area.csv", index = False)

##################################################################################
### Sanity check results against notebook
##################################################################################

print(dc_food_final.shape)
print(neighb_area.shape)
print((time.time() - start_time)/60)