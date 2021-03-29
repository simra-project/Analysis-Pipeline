
import folium

from folium.plugins import MarkerCluster

import geopandas as gpd

from shapely.ops import cascaded_union

from shapely.geometry.multipolygon import MultiPolygon

from shapely.geometry.polygon import Polygon

from statistics import mean

import datetime

import random

import os

import utils # internal import

#*******************************************************************************************************************
# (*) Scatter marker location to prevent overlay

def scatter(lat, lon):

    lat_scatter = random.uniform(-0.0001, 0.0001)

    lon_scatter = random.uniform(-0.0001, 0.0001)

    return [lat + lat_scatter, lon + lon_scatter]

#*******************************************************************************************************************
# (*) Plot polygons onto map.

# This variant follows the following approach to plotting MultiPolygons:
# extract individual Polygons from MultiPolygons and plot these. 

def extractAndPlot (extractable_shape, neighbour_cluster, mmaapp, style, crs, marker_cluster, marker_color):

    if isinstance(extractable_shape, Polygon):
        
        lats, lons = extractable_shape.exterior.coords.xy
            
        poly_swapped = Polygon(zip(lons, lats))

        d = {'geometry': [poly_swapped], 'neighbour_cluster': [neighbour_cluster]}
            
        poly_geoDf = gpd.GeoDataFrame(d, crs=crs)
        
        folium.GeoJson(poly_geoDf, style_function=lambda x: style).add_to(mmaapp)

        lat, lon = extractable_shape.centroid.x, extractable_shape.centroid.y

        folium.Marker(scatter(lat, lon), popup=f'<i>Neighbour Cluster: {neighbour_cluster}</i>', icon=folium.Icon(color=marker_color)).add_to(marker_cluster)
            
    elif isinstance(extractable_shape, MultiPolygon):
            
        individual_polys = list(extractable_shape)
            
        for poly in individual_polys:
        
            extractAndPlot(poly, neighbour_cluster, mmaapp, style, crs, marker_cluster, marker_color)

def plotPolys (df, map, style, marker_cluster, marker_color):

    crs = "EPSG:4326" # CRS = coordinate reference system, epsg:4326 = Europa im Lat/Lon Format

    # Workaround because of different names for the column containing the geometric shape to be plotted, 
    # TODO get rid of this bc it's ugly !!!

    # geomCol = 'poly_geometry' if 'poly_geometry' in df.columns else 'geometry'

    for ind in df.index:

        if df.at[ind, 'neighbour_cluster'] == 999999:

            extractAndPlot(df.at[ind, 'poly_geometry'], df.at[ind, 'neighbour_cluster'], map, {'fillColor': '#ffd700', 'lineColor': '#DAA520'}, crs, marker_cluster, 'orange')

        else:

            extractAndPlot(df.at[ind, 'poly_geometry'], df.at[ind, 'neighbour_cluster'], map, style, crs, marker_cluster, marker_color)

#*******************************************************************************************************************
# (*) Execute all the map jobs in logical order.

def runAllMapTasks (region, small_buf_inconsist, large_buf_inconsist):

    # region, nonIsolatedJunctions, isolatedJunctions, bufferSize

    bbCentroid = utils.paramDict[region]['centroid']

    # I.) Set up our maps

    bbCentroid = utils.paramDict[region]['centroid']

    myMap = folium.Map(location=bbCentroid, zoom_start=15, tiles='cartodbpositron')

    # II.) Plot polys onto their respective maps

    marker_cluster = MarkerCluster().add_to(myMap)

    plotPolys (large_buf_inconsist, myMap, {'fillColor': '#87CEEB', 'lineColor': '#4682B4'}, marker_cluster, 'blue')

    plotPolys (small_buf_inconsist, myMap, {'fillColor': '#3CB371', 'color': '#2E8B57'}, marker_cluster, 'green')

    # III.) Export map as htmls

    # Find out if we're operating in 'segments'-subdirectory or its parent directory,
    # PyPipeline_ (background: we want to write all files related to segments to the
    # segments subdirectory)

    cwd = os.getcwd()

    in_target_dir = utils.inTargetDir(cwd)

    file_name = f'{region}-segs-manualClust_{datetime.date.today()}.html'

    path = utils.getSubDirPath(file_name, "html_maps")

    myMap.save(path)
