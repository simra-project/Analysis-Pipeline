
import folium

import geopandas as gpd

from shapely.ops import cascaded_union

from shapely.geometry.multipolygon import MultiPolygon

from shapely.geometry.polygon import Polygon

from statistics import mean

import os

import utils # internal import

#*******************************************************************************************************************
# (*) Plot polygons onto map.

# This variant follows the following approach to plotting MultiPolygons:
# extract individual Polygons from MultiPolygons and plot these. 

def extractAndPlot (extractableShape, mmaapp, style, crs):

    if isinstance(extractableShape, Polygon):
        
        lats, lons = extractableShape.exterior.coords.xy
            
        poly_swapped = Polygon(zip(lons, lats))
            
        poly_geoDf = gpd.GeoDataFrame(index=[0], crs=crs, geometry=[poly_swapped])
        
        folium.GeoJson(poly_geoDf, style_function=lambda x: style).add_to(mmaapp)
            
    elif isinstance(extractableShape, MultiPolygon):
            
        individualPolys = list(extractableShape)
            
        for poly in individualPolys:
        
            extractAndPlot(poly, mmaapp, style, crs)

def plotPolys_B (df, geomCol, map, style):

    crs = "EPSG:4326" # CRS = coordinate reference system, epsg:4326 = Europa im Lat/Lon Format
    
    for ind in df.index:

        extractAndPlot(df.at[ind, geomCol], map, style, crs)

#*******************************************************************************************************************
# (*) Execute all the map jobs in logical order.

def runAllMapTasks (region, bbCentroid, nonIsolatedJunctions, isolatedJunctions, bufferSize, neighbourParam):

    # I.) Set up our maps

    myMap = folium.Map(location=bbCentroid, zoom_start=15, tiles='cartodbpositron')

    # II.) Plot polys onto their respective maps

    plotPolys_B(nonIsolatedJunctions, 'geometry', myMap, {'fillColor': '#ff1493', 'lineColor': '#F5FFFA'})

    plotPolys_B(isolatedJunctions, 'poly_geometry', myMap, {'fillColor': '#7FFF00', 'lineColor': '#F5FFFA'})

    # III.) Export map as html

    # Find out if we're operating in 'junctions'-subdirectory or its parent directory,
    # PyPipeline_ (background: we want to write all files related to junctions to the
    # junctions subdirectory)

    cwd = os.getcwd()

    in_target_dir = utils.inTargetDir(cwd)

    file_name = f'{region}-jcts-map_buf={bufferSize}_np={neighbourParam}.html'

    path = file_name if in_target_dir else utils.getSubDirPath(file_name)

    myMap.save(path)
