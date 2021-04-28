
from itertools import starmap

from geopandas import GeoSeries

from shapely.geometry import Point

import numpy as np
from multiprocessing import  Pool

import utils_segs as utils

#*******************************************************************************************************************
# (1) Find out which ways don't start and/or end with a junction. Wherever that is the case, we want to 
#     merge segments together in order to get rid of weird breaks - goal is to obtain a clean model of
#     street segments starting and ending at junctions.
#
#     Let an **ODDBALL** be a way that doesn't end or start with a junction (or neither).
#     
#     BELOW SOME CONSIDERATIONS THAT ARE RELEVANT WHEN ALL KINDS OF HIGHWAY TYPES ARE CONSIDERED:
#
#     TBD: we don't want small ways to weirdly be merged together  - e.g., pathways in a park 
#     would be at risk of becoming a weird giant cobweb. 
#     ***Q***: Why could this happen in the first place? - 
#     ***A***: because on our terms, a junction is a junction only if at least two of the highways associated with it are of a larger type.
#
#     Approaches so far:
#     1. allow a segment to become an oddball only if its type is contained in our list of relevantTypes --> nope, this didn't deliver
#     2. incorporate the 'phantom junctions' into oddball definition - those are intersections of more than two ways with less than 
#        two of those being of a relevantType. Hasn't worked out so far.

def oddballWrapper (segmentsdf, jctsdf):

    # these are ALL junctions (i.e., intersections of at least two highways, irrespective of their type)

    #jctids = jctsdf['id'].values 

    # now we also need the LARGER junctions (i.e., intersections of at least two highways of a larger type)

    larger_jcts = jctsdf[jctsdf['junction'] == 'large_junction']

    larger_jctids = larger_jcts['id'].values 

    # ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    def findOddballs(highwaytype, nodes):

        if highwaytype in ['unclassified', 'pedestrian', 'cycleway']:

            return False

        else:
    
            lastNodeIdx = len(nodes) - 1
            
            if not(nodes[0] in larger_jctids):
                
                return True
            
            elif not(nodes[lastNodeIdx] in larger_jctids):
            
                return True
                
            else:
                
                return False

    # Determine oddballs in segments df

    segmentsdf.loc[:,'oddball'] = [x for x in starmap(findOddballs, list(zip(segmentsdf.loc[:,'highwaytype'], segmentsdf.loc[:,'segment_nodes_ids'])))]

    # split the df into two new dfs according to oddball property

    unfoldedOddballs = segmentsdf[segmentsdf['oddball'] == True].copy()
    unfoldedNormies = segmentsdf[segmentsdf['oddball'] == False].copy()

    unfoldedOddballs.reset_index(inplace=True)
    unfoldedOddballs = unfoldedOddballs.drop('index', axis=1)
    unfoldedNormies.reset_index(inplace=True)

    unfoldedOddballs = unfoldedOddballs.fillna(u'unknown').reset_index(drop=True)
    unfoldedNormies = unfoldedNormies.fillna(u'unknown').reset_index(drop=True)

    return unfoldedOddballs, unfoldedNormies

#*******************************************************************************************************************
# (2) Cluster & merge oddball segments: We want to merge oddball segments at those ends where they overlap without a 
#     junction being contained in the intersection. To do so, firstly assign its neighbours to each oddball segment. 
#     A neighbouring segment is a segment whose polygon a segments' polygon intersects with (again, without a junction 
#     being contained in that intersection).

def findNeighbours(unfoldedOddballs, sortingParams, junctionsdf):

    # Sort according to upper left corner; sort by lon (minx) resp lat (maxy) first depending on the bounding box's shape. 

    unfoldedOddballs['minx'] = unfoldedOddballs['poly_geometry'].map(lambda p: p.bounds[0])

    unfoldedOddballs['maxy'] = unfoldedOddballs['poly_geometry'].map(lambda p: p.bounds[3])

    unfoldedOddballs.sort_values(by=sortingParams, inplace=True)

    unfoldedOddballs.reset_index(inplace=True)
    unfoldedOddballs = unfoldedOddballs.drop('index',axis=1)
    unfoldedOddballs.reset_index(inplace=True)

    # these are ALL junctions (i.e., intersections of at least two highways, irrespective of their type)

    junctionlats = junctionsdf.lat.values
    junctionlons = junctionsdf.lon.values

    # now we also need the LARGER junctions (i.e., intersections of at least two highways of a larger type)

    larger_jcts = junctionsdf[junctionsdf['junction'] == 'large_junction']

    larger_junctionlats = larger_jcts.lat.values
    larger_junctionlons = larger_jcts.lon.values
    larger_jctids = larger_jcts['id'].values 

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Define some inner functions we'll need for determining the segments' neighbours.

    ## a) isIntersectionValid: two segments are neighbours if they share a node at either of their ends, with that
    #                           node obviously not being a junction. 

    def sharedNonJunctionNode(outerNodes, innerNodes):
        
        outerLastNodeIdx = len(outerNodes) - 1

        innerLastNodeIdx = len(innerNodes) - 1

        # Scenario 1: the first node belonging to the outer segment is not a junction.
        #             Check if the inner segment contains this node too (at one of its ends).

        if outerNodes[0] not in larger_jctids:

            if (innerNodes[0] == outerNodes[0] or innerNodes[innerLastNodeIdx] == outerNodes[0]):

                return True

        if outerNodes[outerLastNodeIdx] not in larger_jctids:

            if (innerNodes[0] == outerNodes[outerLastNodeIdx] or innerNodes[innerLastNodeIdx] == outerNodes[outerLastNodeIdx]):

                return True

            else:

                return False

    ## b) getNeighbours: unsurprisingly, this function assigns each segment its neighbours (definition of 'neighbour'
    ##                   in this context: see above)

    def getNeighbours(outerNodes, unfoldedOddballs_):
        
        neighbours = []

        for index, row in unfoldedOddballs_.iterrows(): 

            if sharedNonJunctionNode(outerNodes, row['segment_nodes_ids']):

                neighbours.append(index)
                        
        return neighbours

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    '''
    unfoldedOddballs = unfoldedOddballs.dropna(subset=['segment_nodes_ids'])

    print(unfoldedOddballs['segment_nodes_ids'].isnull().values.any())

    unfoldedOddballs['neighbours'] = unfoldedOddballs['segment_nodes_ids'].map(getNeighbours)
    '''

    return unfoldedOddballs

#*******************************************************************************************************************
# (3) Find neighbour clusters (neighbours of neighbours of neighbours ...)

def clusterNeighbours(df):
    
    clusterInd = 0
    
    # Store the indices of rows we've already assigned a cluster to.
    
    included = []
    
    for ind in df.index:
        
        # Do not look at rows we've already assigned clusters to 
        # (at least not in this - the outer - loop. Why?
        # because a cluster detected in the inner loop is complete.)
        
        if ind in included:

            continue

        else:

            currNeighbours = []
            
            # Assign the current cluster index to the row.
        
            df.at[ind, 'neighbour_cluster'] = clusterInd
            
            # Add the current row's index to the list of rows that were already visited.
            
            included.append(ind)
            
            # Initialize list of neighbours in cluster with this row's neighbours.
            # NOTE: 'extend' adds a list to another list while avoiding creating a 
            #       list of lists. 'Append' adds a single element to a list.
        
            currNeighbours.extend(df.at[ind,'neighbours'])
            
            # Add the row's index to the neighbour list too.
            
            currNeighbours.append(ind)
        
            # Now iterate through the df again to find the neighbours' neighbours.

            included = expandNeighbours(df, clusterInd, ind, list(set(currNeighbours)), included)
                    
            # No more extended neighbours, up the cluster numbers
        
            clusterInd += 1

    return df

def expandNeighbours(df, clusterInd, outerLoopInd, currNeighbours, included):

    # Create a queue based on currNeighbours (the neighbours of the data point in the
    # row considered in the outer loop).

    neighbour_queue = []

    for elem in currNeighbours:

        neighbour_queue.append(elem)
    
    while len(neighbour_queue) != 0:

        print("Queue contents before popping: ")

        for q in neighbour_queue:

            print(q)

        # Remove first element from queue

        nextNeighbour = neighbour_queue.pop(0)

        print("Queue contents after popping: ")

        for q in neighbour_queue:

            print(q)

        # Add nextNeighbour to the list of included data points so it won't be
        # considered in the outer loop

        included.append(nextNeighbour)

        # Assign the cluster nr. to nextNeighbour

        df.at[nextNeighbour, 'neighbour_cluster'] = clusterInd

        # Grab the next neighbour's neighbours

        nextNeighsNeighs = df.at[nextNeighbour,'neighbours']

        # Find any distinct neighbours of this neighbour (that aren't already contained in the cluster)

        distinctNewNeighs = [x for x in nextNeighsNeighs if x not in currNeighbours]
        
        # If any distinct new neighbours have been found, add them to the cluster members list (currNeighbours)
        # as well as the queue

        if distinctNewNeighs != []:

            currNeighbours.extend(distinctNewNeighs)

            neighbour_queue.extend(distinctNewNeighs)

        print("Queue contents after extending: ")

        for q in neighbour_queue:

            print(q)

    print("Finished with queue!")
        
    return included

#*******************************************************************************************************************
# (X) Call all the functions required for clustering in logical order.

# def cluster (segmentsdf, junctionsdf, neighbourParam, sortingParams):

def cluster (region, segmentsdf, junctionsdf):

    # 0.) Retrieve parameters from param dictionary

    sorting_params = utils.paramDict[region]["sorting_params"]

    # neighbour_param = utils.paramDict[region]["neighbour_param"]

    # I.) Determine which segments are 'oddballs' (don't start and/or end with a junction)

    oddballs, normies = oddballWrapper(segmentsdf, junctionsdf)

    oddballs.to_pickle('oddball_pickle')

    # II.) Assign each oddball segment its neighbours (other segments it intersects with without a junction being contained
    #      in that intersection).

    oddballsWithNeighbours = findNeighbours(oddballs, sorting_params, junctionsdf)

    # III.) Cluster the oddball segments based on their neighbours

    oddballsWithNeighbours_clustered = clusterNeighbours(oddballsWithNeighbours)

    # IV.) Add a cluster to the isolated segments too (each will have their own, due to their isolation :'( ))

    max_ni_clust = oddballsWithNeighbours_clustered['neighbour_cluster'].max() 

    normies["neighbour_cluster"] = normies.index.map(lambda x: max_ni_clust + x)

    return oddballsWithNeighbours_clustered, normies