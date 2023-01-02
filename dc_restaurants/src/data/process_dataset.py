'''Adds information from dataset #1 and dataset #2 to Zillow neighborhood geojson
    Dataset #1 - Creates summary stats at the neighborhood level
    Dataset #2 - Joins area to calculate restaurants per square foot
'''

import pandas as pd
import geopandas as gpd
import os
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

## Load encoded restaurant license data
dc_food = pd.read_csv("data\\interim\\DC_FoodEstablish_Since2005.csv", low_memory = False)

## Load neighborhood areas
dc_neighborhood_area = pd.read_csv("data\\interim\\neigbh_area.csv", low_memory = False)

## Load geojson as geopandas dataframe
dc_zil_gdf = gpd.read_file("data\\external\\zillow_nb_dc.geojson")    

##################################################################################
###   Functions that streamline summary stat calcs
##################################################################################

## Returns 1 if license is active during time period of interest and specified category
def active(col1, col2, col3, col4, license, date):
    if (col1 == 'Ready to Renew' or col1 == 'Active') and col2 >= date and col3 <= date and col4 == license:
        return 1
    else:
        return 0  
    
## Returns 1 if license is not active, license is within time period of interest and license is specified category

def closed(col1, col2, col3, license, end, start):
    if col1 != 'Ready to Renew' and col1 != 'Active' and col2 <= end and col2 >= start and col3 == license:
        return 1
    else:
        return 0

### If number of food establishments is less than 5, 0 out the percent closed metric
def min_limit(col1, col2):
    if col1 <= 5:
        return 0
    else:
        return col2

## create function that calculate the number of establishments per square mile
def sq_mi(col1,col2):
    if col1 == 0:
        return 0
    else:
        return round(col1/col2,0)

##########################################################################################
###   Create summary stat calcs by DC neighborhood                                ########
##########################################################################################

dc_rest = dc_food[(dc_food.LICENSE_END_DATE >= '2018-01-01') 
                  & (dc_food.LICENSECATEGORY.isin(['Restaurant','Delicatessen']))
                 ].copy()

## Apply functions to create columns for restaurants and delis
dc_rest['active_rest'] = dc_rest.apply(lambda x: active(x['LICENSESTATUS'],x['LICENSE_END_DATE'],x['LICENSE_START_DATE'],x['LICENSECATEGORY'],'Restaurant', '2019-09-01'), axis = 1)
dc_rest['close_18_rest'] = dc_rest.apply(lambda x: closed(x['LICENSESTATUS'],x['LICENSE_END_DATE'],x['LICENSECATEGORY'],'Restaurant', '2018-12-31', '2017-12-31'), axis = 1)
dc_rest['close_19_rest'] = dc_rest.apply(lambda x: closed(x['LICENSESTATUS'],x['LICENSE_END_DATE'],x['LICENSECATEGORY'],'Restaurant', '2019-12-31', '2018-12-31'), axis = 1)

dc_rest['active_deli'] = dc_rest.apply(lambda x: active(x['LICENSESTATUS'],x['LICENSE_END_DATE'],x['LICENSE_START_DATE'],x['LICENSECATEGORY'],'Delicatessen', '2019-09-01'), axis = 1)
dc_rest['close_18_deli'] = dc_rest.apply(lambda x: closed(x['LICENSESTATUS'],x['LICENSE_END_DATE'],x['LICENSECATEGORY'],'Delicatessen', '2018-12-31', '2017-12-31'), axis = 1)
dc_rest['close_19_deli'] = dc_rest.apply(lambda x: closed(x['LICENSESTATUS'],x['LICENSE_END_DATE'],x['LICENSECATEGORY'],'Delicatessen', '2019-12-31', '2018-12-31'), axis = 1)

## Roll-up the data to the neighborhood level
dc_rest_grp = dc_rest.groupby("neighborhood")['active_rest','close_18_rest','close_19_rest','active_deli','close_18_deli','close_19_deli'].sum()

## Create a couple of additional counts
dc_rest_grp['active_tot'] = dc_rest_grp['active_rest'] + dc_rest_grp['active_deli']
dc_rest_grp['close_18_tot'] = dc_rest_grp['close_18_rest'] + dc_rest_grp['close_18_deli']
dc_rest_grp['close_19_tot'] = dc_rest_grp['close_19_rest'] + dc_rest_grp['close_19_deli']
dc_rest_grp['pct_closed_rest'] = 100*round((dc_rest_grp['close_19_rest'] + dc_rest_grp['close_18_rest'])/(dc_rest_grp['close_19_rest'] + dc_rest_grp['close_18_rest']+dc_rest_grp['active_rest']),3)
dc_rest_grp['pct_closed_deli'] = 100*round((dc_rest_grp['close_19_deli'] + dc_rest_grp['close_18_deli'])/(dc_rest_grp['close_19_deli'] + dc_rest_grp['close_18_deli']+dc_rest_grp['active_deli']),3)
dc_rest_grp['pct_closed_tot'] = 100*round((dc_rest_grp['close_19_tot'] + dc_rest_grp['close_18_tot'])/(dc_rest_grp['close_19_tot'] + dc_rest_grp['close_18_tot']+dc_rest_grp['active_tot']),3)

## Replace NAs with 0
dc_rest_grp.fillna(0, inplace = True)

#########################################################################################################
###   Merge the summary stats onto the Zillow GeoPandas dataframe                                ########
#########################################################################################################

### merge the variables of interest into the Geodataframe
dc_gdf = dc_zil_gdf.merge(dc_rest_grp, left_on='name', right_on='neighborhood', how='left')

### merge the area of each neighborhood
dc_gdf = dc_gdf.merge(dc_neighborhood_area)

### if the neighborhood doesn't have any pertinent stats for the time period and category change NA to 0
cols = dc_gdf.columns[6:17] #limit to metric columns we just added in the merge
dc_gdf[cols] = dc_gdf[cols].fillna(0)

dc_gdf['active_tot_sq_mi'] = dc_gdf.apply(lambda x: sq_mi(x['active_tot'],x['sq_mi']), axis = 1)      
dc_gdf['active_rest_sq_mi'] = dc_gdf.apply(lambda x: sq_mi(x['active_rest'],x['sq_mi']), axis=1)      
dc_gdf['active_deli_sq_mi'] = dc_gdf.apply(lambda x: sq_mi(x['active_deli'],x['sq_mi']), axis=1)  

dc_gdf.to_file("data\\processed\\zillow_nb_dc_merged.geojson", driver='GeoJSON')

print(dc_gdf.shape)