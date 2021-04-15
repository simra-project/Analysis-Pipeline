import folium 

import geopandas as gpd

from shapely.ops import cascaded_union

from shapely.geometry.multipolygon import MultiPolygon

from shapely.geometry.polygon import Polygon

from shapely.geometry import Point

import numpy as np

import os

import datetime

import utils_segs as utils # internal import

#*******************************************************************************************************************
# (*) Plot polygons onto map.

# This variant follows the following approach to plotting MultiPolygons:
# extract individual Polygons from MultiPolygons and plot these. 

def extractAndPlot (extractableShape, mmaapp, style, crs, highwaytype, highwayname, highwayId, neighbour_cluster):
    
    if isinstance(extractableShape, Polygon):
        
        lats, lons = extractableShape.exterior.coords.xy
            
        poly_swapped = Polygon(zip(lons, lats))
            
        poly_geoDf = gpd.GeoDataFrame(index=[0], crs=crs, geometry=[poly_swapped])
        
        folium.GeoJson(poly_geoDf, style_function=lambda x: style, tooltip=f"Highwayname: {highwayname}, highwatype: {highwaytype}, id: {highwayId}, neighbour cluster: {neighbour_cluster}").add_to(mmaapp)
            
    elif isinstance(extractableShape, MultiPolygon):
            
        '''
        individualPolys = list(extractableShape)
            
        for poly in individualPolys:
        
            extractAndPlot(poly, mmaapp, style, crs, highwaytype)
        '''
        minx, miny, maxx, maxy = extractableShape.bounds

        multipoly_lats = [minx, maxx, minx]

        multipoly_lons = [miny, maxy, miny]

        poly = Polygon(zip(multipoly_lons, multipoly_lats))

        poly_geoDf = gpd.GeoDataFrame(index=[0], crs=crs, geometry=[poly])
        
        folium.GeoJson(poly_geoDf, style_function=lambda x: {'fillColor': '#FFD700', 'lineColor': '#F5FFFA'}, tooltip=f"Highwayname: {highwayname}, highwatype: {highwaytype}, id: {highwayId}, neighbour cluster: {neighbour_cluster}").add_to(mmaapp)

def plotPolys (df, geomCol, mmaapp, style) :
    
    crs = "EPSG:4326" # CRS = coordinate reference system, epsg:4326 = Europa im Lat/Lon Format

    for ind in df.index:
        
        extractAndPlot(df.at[ind, geomCol], mmaapp, style, crs, df.at[ind, 'highwaytype'], df.at[ind, 'highwayname'], df.at[ind, 'id'], df.at[ind, 'neighbour_cluster'])

#*******************************************************************************************************************
# (*) Execute all the map jobs in logical order.

def runAllMapTasks (region, bbCentroid, oddballs, normies, neighbourParam):

    # I.) Set up our maps

    myMap = folium.Map(location=bbCentroid, zoom_start=15, tiles='cartodbpositron', prefer_canvas=True)

    # II.) Plot polys onto their respective maps

    plotPolys(oddballs, 'geometry', myMap, {'fillColor': '#ff1493', 'lineColor': '#F5FFFA'})

    plotPolys(normies, 'poly_geometry', myMap, {'fillColor': '#7FFF00', 'lineColor': '#F5FFFA'})

    # III.) Export map as html

    # Find out if we're operating in 'segments'-subdirectory or its parent directory,
    # PyPipeline_ (background: we want to write all files related to segments to the
    # segments subdirectory)

    cwd = os.getcwd()

    in_target_dir = utils.inTargetDir(cwd)

    file_name = f'{region}-segs-map_np={neighbourParam}_{datetime.date.today()}.html'

    path = utils.getSubDirPath(file_name, "html_maps")

    myMap.save(path)

    return myMap