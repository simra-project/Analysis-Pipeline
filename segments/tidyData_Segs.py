# import mapSegs

import geopandas as gpd

import os

#os.environ["MODIN_ENGINE"] = "ray"  # Modin will use Ray
#import modin.pandas as pd

import pandas as pd

import numpy as np

from shapely.geometry import Polygon, MultiPolygon

import mapSegs

import utils_segs as utils

def tidyItUp(region, oddballs, normies):

    # 0.) Retrieve params from dict

    bb_centroid = utils.paramDict[region]["centroid"]

    neighbour_param = utils.paramDict[region]["neighbour_param"]

    ## a) Merge neighbour clusters: dissolving geometric shapes according to a shared property can be achieved using [geopandas](https://www.earthdatascience.org/workshops/gis-open-source-python/dissolve-polygons-in-python-geopandas-shapely/)

    # Make a df with cluster ID and polygon only so we can use geopandas' dissolve method to merge the poly shapes for each cluster.

    geoOddballs = gpd.GeoDataFrame(oddballs.neighbour_cluster, geometry=oddballs.poly_geometry)

    oddballClusters = geoOddballs.dissolve(by='neighbour_cluster')

    ## (b) Join the remaining df columns too using pandas groupby and merge everything together

    oddballs = oddballs.drop(["index","lats","lons","coords","oddball","poly_geometry","poly_vertices_lats","poly_vertices_lons","neighbours"], axis=1)

    oddballs = oddballs.groupby('neighbour_cluster', as_index = False).agg({'id': 'sum', 'highwayname': 'sum', 'highwaytype': 'sum', 'highwaylanes': 'sum','lanes:backward': 'sum', 'segment_nodes_ids': 'sum', 'seg_length': 'sum'})

    # Remove duplicates from columns

    oddballs['highwayname'] = oddballs['highwayname'].apply(lambda x: list(set(x)))

    oddballs['highwaytype'] = oddballs['highwaytype'].apply(lambda x: list(set(x)))

    oddballs['highwaylanes'] = oddballs['highwaylanes'].apply(lambda x: list(set(x)))

    oddballs['lanes:backward'] = oddballs['lanes:backward'].apply(lambda x: list(set(x)))

    oddballMerge = pd.merge(oddballs, oddballClusters, on='neighbour_cluster')

    ## c) Plot !

    myMap = mapSegs.runAllMapTasks (region, bb_centroid, oddballMerge, normies, neighbour_param)

    ## d) Extract the vertices of shapes. This involves our delightful procedure of exploding MultiPolygons into their
    ##    components because they suck and we don't want them in our df!!!!
    ##    (Why do they suck? Because they're just weird quadratic shapes, i.e. the geometry is really imprecise,
    ##    we can't extract any nice lists of coordinates describing their outlines but only minx/miny/maxx/maxy)

    oddballMerge['extracted_polys'] = np.empty((len(oddballMerge), 0)).tolist()

    # Function for recursively unpacking MultiPolygons into the individual Polygons they consist of.

    def extractPolys (ind, extractableShape):
    
        # Is the shape already a polygon? NEAT, add to dict at the
        # respective index
        
        if isinstance(extractableShape, Polygon):
            
            oddballMerge.at[ind,'extracted_polys'].append(extractableShape)
                
        # Oh nooooo, it's a MultiPolygon! Call this function recursively until
        # we're down to polygon-level for every component of the MultiPolygon.
                
        elif isinstance(extractableShape, MultiPolygon):
                
            multiPolyContents = list(extractableShape)
                
            for poly in multiPolyContents:
            
                extractPolys(ind, poly)

    polysWithMPs = oddballMerge.geometry.values

    indices = oddballMerge.index.values

    np.vectorize(extractPolys)(indices, polysWithMPs) # Output is an array of Nones bc this is a void function 

    # Here comes our beloved df 'exploding' - i.e., rows whose geometry property corresponds to a MultiPolygon are unfolded
    # into multiple rows, one per Polygon (a MultiPolygon is a collection of Polygons)

    polyLists = oddballMerge.extracted_polys.values.tolist()
    lens = [len(r) for r in polyLists]
    neighClusters = np.repeat(oddballMerge.neighbour_cluster, lens)
    ids = np.repeat(oddballMerge.id, lens)
    names = np.repeat(oddballMerge.highwayname, lens)
    types = np.repeat(oddballMerge.highwaytype, lens)
    lanes = np.repeat(oddballMerge.highwaylanes, lens)
    lanesBw = np.repeat(oddballMerge['lanes:backward'], lens)
    nodesIds = np.repeat(oddballMerge.segment_nodes_ids, lens)
    segLens = np.repeat(oddballMerge.seg_length, lens)

    explodedOddballs = pd.DataFrame(np.column_stack((neighClusters, ids, names, types, lanes, lanesBw, nodesIds, segLens, np.concatenate(polyLists))), columns=['neighbour_cluster','id','highwayname','highwaytype','highwaylanes','lanes:backward','segment_nodes_ids','seg_length','poly_geometry'])

    # Retrieve lists of lats & lons from the Polygons

    polyLats = explodedOddballs['poly_geometry'].map(lambda x: x.exterior.coords.xy).map(lambda x: x[0])

    polyLons = explodedOddballs['poly_geometry'].map(lambda x: x.exterior.coords.xy).map(lambda x: x[1])

    explodedOddballs.loc[:,'poly_vertices_lats'], explodedOddballs.loc[:,'poly_vertices_lons'] = polyLats, polyLons

    ## d) Merge back together with the normie-df.

    unfoldedNormies = normies.drop(["index","lats","lons","coords","oddball"], axis=1)

    completeSegments = pd.concat([explodedOddballs, unfoldedNormies], ignore_index = True, sort = False)

    completeSegments.loc[:,'poly_vertices_lats'] = completeSegments['poly_vertices_lats'].map(lambda x: list(x))

    completeSegments.loc[:,'poly_vertices_lons'] = completeSegments['poly_vertices_lons'].map(lambda x: list(x))

    return completeSegments, myMap