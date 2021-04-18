
import mapJcts

import geopandas as gpd

import pandas as pd

import numpy as np

from shapely.geometry import Polygon, MultiPolygon

def explodeAndConcat(nonIsolatedMerge, isolatedJunctions):

    ## d) Redo the geometry. This involves our delightful procedure of exploding MultiPolygons into their
    ##    components because they suck and we don't want them in our df!!!!
    ##    (Why do they suck? Because they're just weird quadratic shapes, i.e. the geometry is really imprecise,
    ##    we can't extract any nice lists of coordinates describing their outlines but only minx/miny/maxx/maxy)

    nonIsolatedMerge.loc[:,'poly_vertices_lats'] = ''

    nonIsolatedMerge.loc[:,'poly_vertices_lons'] = ''

    ### Set up a dict as interim storage. Yup I know it's quick and dirty and not very elegant to do this

    nonIsolatedMerge['extracted_polys'] = np.empty((len(nonIsolatedMerge), 0)).tolist()

    # During merging, some MultiPolygons may have emerged. We need to 'explode' the df according to these
    # objects, i.e. extract the individual Polygons the MultiPolygon consists of and duplicate the corresponding
    # other column values so we can give each of the extracted Polygons its own row.

    def extractPolys (ind, extractableShape):
    
        # Is the shape already a polygon? NEAT, add to dict at the
        # respective index
        
        if isinstance(extractableShape, Polygon):
            
            nonIsolatedMerge.at[ind,'extracted_polys'].append(extractableShape)
                
        # Oh nooooo, it's a MultiPolygon! Call this function recursively until
        # we're down to polygon-level for every component of the MultiPolygon.
                
        elif isinstance(extractableShape, MultiPolygon):
                
            multiPolyContents = list(extractableShape)
                
            for poly in multiPolyContents:
            
                extractPolys(ind, poly)

    polysWithMPs = nonIsolatedMerge.geometry.values

    indices = nonIsolatedMerge.index.values

    np.vectorize(extractPolys)(indices, polysWithMPs)

    polyLists = nonIsolatedMerge.extracted_polys.values.tolist()
    lens = [len(r) for r in polyLists]
    ids = np.repeat(nonIsolatedMerge.id, lens)
    lats = np.repeat(nonIsolatedMerge.lat, lens)
    lons = np.repeat(nonIsolatedMerge.lon, lens)
    hwIds = np.repeat(nonIsolatedMerge.highwayids, lens)
    hwNames = np.repeat(nonIsolatedMerge.highwaynames, lens)
    hwTypes = np.repeat(nonIsolatedMerge.highwaytypes, lens)
    hwLanes = np.repeat(nonIsolatedMerge.highwaylanes, lens)
    hwLanesBw = np.repeat(nonIsolatedMerge.highwaylanesBw, lens)
    neighs = np.repeat(nonIsolatedMerge.neighbours, lens)
    neighbourClusters = np.repeat(nonIsolatedMerge.neighbour_cluster, lens)

    explodedNonIsolatedJunctions = pd.DataFrame(np.column_stack((ids, lats, lons, hwIds, hwNames, hwTypes, hwLanes, hwLanesBw, np.concatenate(polyLists), neighs, neighbourClusters)), columns=['id','lat','lon','highwayids','highwaynames','highwaytypes','highwaylanes','highwaylanesBw','poly_geometry', 'neighbours', 'neighbour_cluster'])

    polyLats = explodedNonIsolatedJunctions['poly_geometry'].map(lambda x: x.exterior.coords.xy).map(lambda x: x[0]).map(lambda x: list(x))

    polyLons = explodedNonIsolatedJunctions['poly_geometry'].map(lambda x: x.exterior.coords.xy).map(lambda x: x[1]).map(lambda x: list(x))

    explodedNonIsolatedJunctions.loc[:,'poly_vertices_lats'], explodedNonIsolatedJunctions.loc[:,'poly_vertices_lons'] = polyLats, polyLons

    explodedNonIsolatedJunctions_reordered = explodedNonIsolatedJunctions.reindex(columns=['id','lat','lon','highwayids','highwaynames','highwaytypes','highwaylanes','highwaylanesBw','poly_geometry','poly_vertices_lats','poly_vertices_lons','neighbours','neighbour_cluster'])

    ## d) Merge back together with the isolatedJunctions.

    completeJunctions = pd.concat([explodedNonIsolatedJunctions_reordered, isolatedJunctions], ignore_index = True, sort = False)

    # completeJunctions = completeJunctions.drop("neighbours", axis = 1)

    return completeJunctions
    

def tidyItUp(region, segMap, bbCentroid, nonIsolatedJunctions, isolatedJunctions, bufferSize, neighbourParam):

    # ********************************************************************************************************************

    ## a) Merge neighbour clusters: dissolving geometric shapes according to a shared property can be achieved using [geopandas](https://www.earthdatascience.org/workshops/gis-open-source-python/dissolve-polygons-in-python-geopandas-shapely/)

    # Make a df with cluster ID and polygon only so we can use geopandas' dissolve method to merge the poly shapes for each cluster.

    geoJunctions = gpd.GeoDataFrame(nonIsolatedJunctions.neighbour_cluster, geometry=nonIsolatedJunctions.poly_geometry)

    junctionClusters = geoJunctions.dissolve(by='neighbour_cluster')

    ## (b) Join the remaining df columns too using pandas groupby and merge everything together

    nonIsolatedJunctions = nonIsolatedJunctions.drop(["poly_vertices_lats", "poly_vertices_lons", "poly_geometry"], axis=1)

    # nonIsolatedJunctions = nonIsolatedJunctions.groupby('neighbour_cluster', as_index = False).agg({'id': lambda x: ', '.join(map(str, x)), 'lat': lambda x: ', '.join(map(str, x)), 'lon': lambda x: ', '.join(map(str, x)), 'highwayids': 'sum', 'highwaynames': 'sum', 'highwaytypes': 'sum', 'highwaylanes': 'sum','highwaylanesBw': 'sum', 'neighbours': 'sum'})

    nonIsolatedJunctions = nonIsolatedJunctions.groupby('neighbour_cluster', as_index = False).agg({'id': 'sum', 'lat': lambda x: ', '.join(map(str, x)), 'lon': lambda x: ', '.join(map(str, x)), 'highwayids': 'sum', 'highwaynames': 'sum', 'highwaytypes': 'sum', 'highwaylanes': 'sum','highwaylanesBw': 'sum', 'neighbours': 'sum'})   

    nonIsolatedJunctions['highwaynames'] = nonIsolatedJunctions['highwaynames'].apply(lambda x: list(set(x)))

    nonIsolatedJunctions['highwaytypes'] = nonIsolatedJunctions['highwaytypes'].apply(lambda x: list(set(x)))

    nonIsolatedJunctions['highwaylanes'] = nonIsolatedJunctions['highwaylanes'].apply(lambda x: list(set(x)))

    nonIsolatedJunctions['highwaylanesBw'] = nonIsolatedJunctions['highwaylanesBw'].apply(lambda x: list(set(x)))

    # Same thing for isolatedJunctions

    isolatedJunctions['highwaynames'] = isolatedJunctions['highwaynames'].apply(lambda x: list(set(x)))

    isolatedJunctions['highwaytypes'] = isolatedJunctions['highwaytypes'].apply(lambda x: list(set(x)))

    isolatedJunctions['highwaylanes'] = isolatedJunctions['highwaylanes'].apply(lambda x: list(set(x)))

    isolatedJunctions['highwaylanesBw'] = isolatedJunctions['highwaylanesBw'].apply(lambda x: list(set(x)))

    # nonIsolatedJunctions.to_csv(region + '_junctions_FIVE.csv', index=False, sep="|")

    nonIsolatedMerge = pd.merge(nonIsolatedJunctions, junctionClusters, on='neighbour_cluster')

    ## c) Plot !

    totalMap = mapJcts.runAllMapTasks(region, segMap, bbCentroid, nonIsolatedMerge, isolatedJunctions, bufferSize, neighbourParam)

    completeJunctions = explodeAndConcat(nonIsolatedMerge, isolatedJunctions)

    return completeJunctions, totalMap