'''Creates map from geojson
'''

import folium
from folium import plugins
import branca

__author__ = "Lindsay Allen"
__version__ = "1.0.1"
__maintainer__ = "Lindsay Allen"
__status__ = "Development"

def dc_map(dc_gdf, variable, name):
    ###################################################################
    ### 3.1 Initiate the map
    ###################################################################
    
    centroid=dc_gdf.geometry.centroid ## identifies the center point of all the neighborhood shapes 

    m=folium.Map(location=[centroid.y.mean(), centroid.x.mean()], zoom_start=12) ## initiaes a map based on the centroid
    
    ###################################################################
    ### Creating the breaks for the colorscale
    ###################################################################
    
    # create df with neighborhood name and variable of interest, sorted from largest to smallest
    df = dc_gdf[['name', variable]].sort_values(by = variable, ascending = False) 
    
    # reset index so that the largest value corresponds to row 0 and smallest to row 136
    df.reset_index(inplace = True)
    leg_brks = list(df[df.index.isin([0,4,9,19,29,49])][variable]) # identify the value of the var by index position
    
    # make the smallest value of the scale be 0
    leg_brks.append(0)
    leg_brks.sort() # sort from smallest to largest
 
    ###################################################################
    ### 3.2 Creating the colormap
    ###################################################################
 
    # sets coloring scale range to variable min and max
    colorscale = branca.colormap.linear.YlOrRd_09.scale(dc_gdf[variable].min(), dc_gdf[variable].max()) 
    colorscale = colorscale.to_step(n = 6, quantiles = leg_brks) ## sets quantile breaks 
    colorscale.caption = name ## adds name for legend

    ###################################################################
    ### 3.3 Folium GeoJson Class
    ###################################################################
    
    folium.GeoJson(dc_gdf, ## GeoPandas dataframe
               name="Washington DC",
                   
               ## controls the fill of the geo regions; applying colorscale based on variable
               style_function=lambda x: {"weight":1
                                         , 'color': '#545453'
                                        # this looks up name of neighborhood in GeoJSON and colors
                                        # based on the value of the variable we're plotting
                                         , 'fillColor':'#9B9B9B' if x['properties'][variable] == 0 
                                         else colorscale(x['properties'][variable])
                                         ## similarly opacity is increased if value is 0
                                         , 'fillOpacity': 0.2 if x['properties'][variable] == 0 
                                         else 0.5},
                   
               ## changes styling of geo regions upon hover
               highlight_function=lambda x: {'weight':3, 'color':'black', 'fillOpacity': 1}, 
               
                ## tooltip can include information from any column in the GeoPandas dataframe   
                tooltip=folium.features.GeoJsonTooltip(
                fields=['name', 'active_tot', 'active_tot_sq_mi', variable],
                aliases=['Neighborhood:', '# Active Restaurants + Delis:', '# Active Per Sq Mi', name])
              ).add_to(m)

    ## add colorscale to map so that it appears as the legend
    colorscale.add_to(m)
    
    return m