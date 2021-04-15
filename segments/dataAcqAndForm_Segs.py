
import os

#os.environ["MODIN_ENGINE"] = "dask"  # Modin will use Dask
#os.environ["MODIN_ENGINE"] = "ray"  # Modin will use Ray
#import modin.pandas as pd

import pandas as pd

import requests
import numpy as np
import sys

import utils_segs as utils

# ********************************************************************************************************************
    
tags = ['motorway','trunk','primary','secondary','secondary_link','tertiary','tertiary_link','living_street','residential', 'unclassified', 'pedestrian', 'cycleway']

# (1) Get data from OSM, input param = bounding box

def getFromOverpass(bbox):

    ##############################################################################################################
    # a) Extract bb corners

    # Links unten
    minLat = bbox[1]
    minLon = bbox[0]

    # Rechts oben
    maxLat = bbox[3]
    maxLon = bbox[2]

    ##############################################################################################################
    # b) Construct the Overpass Query String: Request from [Overpass-Turbo](http://overpass-turbo.eu/)

    # 'unclassified', 'pedestrian', 'cycleway'
    objects = ['way'] # like way, node, relation

    compactOverpassQLstring = '[out:json][timeout:60];('
    for tag in tags:
        for obj in objects:
            compactOverpassQLstring += '%s["highway"="%s"](%s,%s,%s,%s);' % (obj, tag, minLat, minLon, maxLat, maxLon)
    compactOverpassQLstring += ');out body;>;out skel qt;'

    osmrequest = {'data': compactOverpassQLstring}

    #osmurl = 'http://overpass-api.de/api/interpreter'

    osmurl = 'http://vm3.mcc.tu-berlin.de:8088/api/interpreter'

    osm = requests.get(osmurl, params=osmrequest)

    ##############################################################################################################
    # c)  Reformat the JSON to fit in a Pandas Dataframe

    osmdata = osm.json()
    osmdata = osmdata['elements']

    nodes = []
    ways = []

    for dct in osmdata:
        if dct['type']=='way':
            for key, val in dct['tags'].items():
                dct[key] = val
            del dct['tags']
            ways.append(dct)
        else:
            nodes.append(dct)

    return ways, nodes # resp osmdata

# ********************************************************************************************************************
# (2) Construct a df containing highways (streets, way objects) from the raw osmdata

# def getHighwayDf(osmdata):

def getHighwayDf(ways):

    # osmdf = pd.DataFrame(osmdata)

    highwaydf = pd.DataFrame(ways)[['highway','id','lanes','lanes:backward','name','nodes']].dropna(subset=['name','highway'], how='any')

    # 'id', 'highway', 'lanes', 'lanes:backward', 'name', 'maxspeed', 'nodes', 'ref'

    # Zu kleine Straßen raus werfen:

    highwaydf = highwaydf[highwaydf['highway'].isin(tags)]

    # Replace `NaN` with word `unknown` and reset the index:

    highwaydf = highwaydf.fillna(u'unknown').reset_index(drop=True)

    # PROBABLY NOT BC NEED UNIQUE 
    # Map ids to list to facilitate cluster comparison in manualClusterPrep
    # COMMENT OUT TO PREVENT THIS

    highwaydf['id'] = highwaydf['id'].map(lambda i: [i])

    # NEW AS OF 15/04: also map other properties to list so they can be aggregated without duplicates

    highwaydf['name'] = highwaydf['name'].map(lambda i: [i])

    highwaydf['highway'] = highwaydf['highway'].map(lambda i: [i])

    highwaydf['lanes'] = highwaydf['lanes'].map(lambda i: [i])

    highwaydf['lanes:backward'] = highwaydf['lanes:backward'].map(lambda i: [i])

    # *********************************************************************
    
    return highwaydf

# ********************************************************************************************************************
# (3) Construct a df containing nodes from the raw osmdata - this project is concerned with highways rather than
#     nodes, but we need the node data to enrich our highwaydf with information that is only contained in node objects
#     (specifically, highways in OSM consist in lists of nodes, which are represented as ids. Only the node objects
#     themselves contain the geospatial coordinates corresponding to node ids. Hence we need a nodesdf in order to 
#     map the highways' lists of node ids onto the node coordinates).
#     -
#     Return a dictionary structure containing node ids as keys and their coords as values for easy lookup.

def getCoordsFromNodes(nodes):
        
    nodesdf = pd.DataFrame(nodes)

    idCoords_dict = pd.Series(list(zip(nodesdf.lat.values,nodesdf.lon.values)),index=nodesdf.id).to_dict()

    return idCoords_dict

# ********************************************************************************************************************
# (0) Call all the functions in this script in logical order.

def metaFunc(bbox, region):

    osmdata, nodes = getFromOverpass(bbox)

    highwaydf = getHighwayDf(osmdata)

    idCoords_dict = getCoordsFromNodes(nodes)

    # Read the junctions data from csv that was produced by the junctions sub-project 
    # and is therefore located in PyPipeline_/junctions.
    # !!!!! Be sure to execute the junctions project first before executing the 
    #       segments project for the same region !!!!
    # (Otherwise, there might be no file to read.)
    # TODO is this reasonable?

    subdir_path = utils.getJunctionsDirPath(f"{region}_junctions_for_segs.csv", "csv_data")

    # Notify user if junctions_for_segs.csv is unavailable as the junctions project hasn't been
    # executed before the segments fraction
    try:
        junctionsdf = pd.read_csv(subdir_path)
    except FileNotFoundError: 
        print("Junctions file wasn't found! Please execute OSM_jcts.py for this region to generate it.")
        sys.exit()
    
    return highwaydf, junctionsdf, idCoords_dict