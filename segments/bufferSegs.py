
import pyproj
from pyproj import CRS
from pyproj import Proj

from functools import partial

import geopandas as gpd
from geopandas import GeoSeries

import shapely
from shapely.ops import transform
from shapely.geometry import CAP_STYLE, JOIN_STYLE
from shapely.geometry import LineString
from shapely.geometry import Polygon
from shapely.geometry import MultiPolygon
from shapely.geometry import Point

import numpy as np

#*******************************************************************************************************************
# (0) Define some functions the actual buffer-function requires.

def roadWidth (roadType, buffer_size) :
         switcher = {
                 'motorway': 9,
                 'trunk': 8,
                 'primary': 7,
                 'secondary' : 6,
                 'tertiary' : 5,
                 'unclassified': 4.5,
                 'residential' : 6,
                 'motorway_link': 7.5,
                 'trunk_link': 7.5,
                 'primary_link': 7.5,
                 'secondary_link': 6.5,
                 'tertiary_link': 5.5,
                 'living_street': 6.5,
                 'service': 5.5,
                 'pedestrian': 6.5,
                 'track': 2.5,
                 'bus_guideway': 5.5,
                 'escape': 5.5,
                 'raceway': 6.5,
                 'road': 6.5,
                 'footway': 1.5,
                 'bridleway': 2.5,
                 'steps': 2.5,
                 'path': 2.5,
                 'cycleway': 1.5
             }
         return (buffer_size * switcher.get(roadType[0], 6.5))

# A little more cumbersome as in case of the junctions, we have to differentiate when creating 2D-shapes 
# from the segment data: there might be segments of length 1, which LineStrings can't be projected from (only Points).

def get2DGeom(coords):
    
    if len(coords) > 1: 
       
        return LineString(list(zip(coords[0],coords[1])))
    
    else:
        
        return Point(coords[0][0],coords[1][0])

# ********************************************************************************************************************
# (1) Let the buffer magic happen!!!!

# In Python, loops are slow because many things happen at run time - if we use loops that operate element-wise,
# type-checking (and presumably other things) are done for every element => sloooooow!
# 
# If we apply function to whole data frame columns (= pd.Series) or, even better, numpy arrays, checks are only done
# once for every Series/array => faaaaaast!

def bufferize(segmentsdf, buffer_size):

    segmentsdf.loc[:,'poly_geometry'] = segmentsdf['coords'].map(get2DGeom)

    # Get the Points/LineStrings representing segments as 2D geometric objects as a GeoSeries to allow for vectorized
    # processing

    nonbufferedGeom = GeoSeries(segmentsdf.poly_geometry)

    # Set coordinate reference system and project to meters for buffering

    nonbufferedGeom.crs = "epsg:4326"

    segs_proj = nonbufferedGeom.to_crs(3035)

    # Get highwaytypes as vector and map onto their respective widths

    highwaytypes = segmentsdf.highwaytype.values

    highwaywidths = np.vectorize(roadWidth)(highwaytypes, buffer_size)

    # Buffer segments into 3 D according to highwaywidths

    bufferedSegs = segs_proj.buffer(highwaywidths, cap_style=3)

    # Super important: if preserve_topology is set to False, the Douglas-Peucker Algorithm is used for simplification.
    # This is faster, but results in some polygons having an exterior of 'None' ... which in turn causes the extration of 
    # the polygon lats and lons to fail.

    # Simplify so we don't have 65 quadrillion coordinates per polygon

    simplified_segs = bufferedSegs.simplify(7, preserve_topology=True)

    # Project back to lat/lon coordinate reference system

    reprojected_segs = simplified_segs.to_crs(4326)

    # Store in df

    segmentsdf.loc[:,'poly_geometry'] = reprojected_segs

    # Extract poly vertices and store in df as well

    polyLats = reprojected_segs.map(lambda x: x.exterior.coords.xy).map(lambda x: x[0])

    polyLons = reprojected_segs.map(lambda x: x.exterior.coords.xy).map(lambda x: x[1])

    segmentsdf.loc[:,'poly_vertices_lats'], segmentsdf.loc[:,'poly_vertices_lons'] = polyLats, polyLons

    return segmentsdf