
from itertools import starmap

from collections import Counter

import numpy as np

import utils

# ## Cluster junctions

#*******************************************************************************************************************
# (1) Define functionality for determining a junction's neighbours

# a) Sort the df by the junctions' lat/lon so we can search for neighbours more efficiently. 

def sortByLocation(junctionsdf, sortingParams):

    junctionsdf.sort_values(by=sortingParams,inplace=True)

    junctionsdf.reset_index(inplace=True, drop=True)

    return junctionsdf

# b) Check if the overlap of two junction polygons is above a specified threshold - could be parameterized as well,
#    of course (didn't seem necessary so far, but might be done in the future.)

def largeIntersection(poly1, poly2):
    return poly1.intersects(poly2) and ((poly1.intersection(poly2).area/poly1.area)*100) > 8

# c) Check if two junctions share a square (which means they should end up in the same cluster)
def sharedSquare(lst1, lst2): 
    lst3 = [value for value in lst1 if value in lst2]
    if lst3 != []:
        for elem in lst3:
            if 'platz' in elem or 'Platz' in elem:
                return True
    return False

# c) Put it all together to assign its neighbours to each junction

def neighbourFindingWrapper(junctionsdf):

    def getNeighbours(outerInd, outerPoly, outerHighways):
    
        neighbours = []

        # Generously look at the 150 rows above and below the current row 
        # when looking for neighbours (in the df sorted by lat/lon)

        lower = max(outerInd-150, 0)
        
        upper = min(outerInd+150, len(junctionsdf)-1)
        
        # Use buffer trick if polygon is invalid
        # https://stackoverflow.com/questions/13062334/polygon-intersection-error-in-shapely-shapely-geos-topologicalerror-the-opera
        
        if not(outerPoly.is_valid):
            
            outerPoly = outerPoly.buffer(0)
        
        for innerInd in range(lower, upper+1):
            
            innerPoly = junctionsdf.at[innerInd,'poly_geometry']
            
            # Use buffer trick if polygon is invalid
            
            if not(innerPoly.is_valid):
            
                innerPoly = innerPoly.buffer(0)
            
            innerHighways = junctionsdf.at[innerInd,'highwaynames']
                
            if outerPoly != innerPoly:
                    
                squareInCommon = sharedSquare(outerHighways, innerHighways)
                    
                if largeIntersection(outerPoly, innerPoly): neighbours.append(innerInd)
                    
                elif  (outerPoly.intersects(innerPoly) and squareInCommon): neighbours.append(innerInd)                
                        
        return neighbours

    junctionsdf['neighbours'] = [x for x in starmap(getNeighbours, list(zip(junctionsdf.index,junctionsdf['poly_geometry'],junctionsdf['highwaynames'])))]

    

    return junctionsdf

#*******************************************************************************************************************
# (2) Split the df according to 'junction has/does not have neighbours'

def splitDf (junctionsdf):

    ## a) Deal with nonIsolatedJunctions

    ###### NOTE: the '.copy()' tells pandas we're creating copies of the original df; doing so prevents the 'settings with copy warning'. 

    nonIsolatedJunctions = junctionsdf.loc[junctionsdf['neighbours'].map(lambda d: len(d)) > 0, :].copy()

    ## b) Deal with isolatedJunctions

    isolatedJunctions = junctionsdf.loc[junctionsdf['neighbours'].map(lambda d: len(d)) == 0, :].copy()

    isolatedJunctions.reset_index(inplace=True, drop=True)

    #isolatedJunctions = isolatedJunctions.drop('level_0', axis=1)

    return nonIsolatedJunctions, isolatedJunctions

#*******************************************************************************************************************
# (3) Functionality for performing the actual clustering on nonIsolatedJunctions

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

        print(type(nextNeighsNeighs))

        print(type(currNeighbours))

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

# --------------------------------------------------------------------------------

def clusterNeighbours(df):
    
    clusterInd = 0
    
    # Store the indices of rows we've already assigned a cluster to.
    
    included = []
    
    for ind in df.index:
        
        # Do not look at rows we've already assigned clusters to 
        # (at least not in this - the outer - loop)
        
        if ind in included:

            continue

        else:

            currNeighbours = []
            
            # Assign the current cluster index to the row.
        
            df.at[ind,'neighbour_cluster'] = clusterInd
            
            # Add the current row's index to the list of rows that were already visited.
            
            included.append(ind)
            
            # Initialize list of neighbours in cluster with this row's neighbours.
        
            currNeighbours.extend(df.at[ind,'neighbours'])
            
            # Add the row's index to the neighbour list too.
            
            currNeighbours.append(ind)
            
            #if not (currNeighbours == [] or np.isnan(currNeighbours)):
        
            # Now iterate through the df again to find the neighbours' neighbours.

            included = expandNeighbours(df, clusterInd, ind, list(set(currNeighbours)), included)
                    
            # No more extended neighbours, up the cluster numbers
        
            clusterInd += 1

    return df

#*******************************************************************************************************************
# (4) Separate undesired merges

def clusterCorrection(nonIsolatedJunctions):

    nonIsolatedJunctions.loc[:,'unmerge'] = ''

    ## a) Set up some stuff that will help us find out where clustering produced undesired results

    ### Aggregate highwaynames and -types in each cluster

    highwaysPerCluster = nonIsolatedJunctions[['highwaynames','highwaytypes','neighbour_cluster']].copy()

    highwaysPerClusterDict = highwaysPerCluster.groupby('neighbour_cluster').agg('sum').to_dict() 

    #### Determine the size of neighbour clusters

    membersPerCluster = nonIsolatedJunctions.groupby('neighbour_cluster').size().to_dict()

    ### Set up a function for determining if a junction is located at a large highway:

    def largeHighwayJunction(highwayTypeList, clusterSize):
    
        largeBois = ['primary','secondary','secondary_link']
    
        return len([s for s in highwayTypeList if any(xs in s for xs in largeBois)]) >= (clusterSize - 1)

    ### Set up a function for determining if a list of highwaynames contains the word 'platz'/'Platz' (square):
    ### [obvsly this one needs to be adapted for non-German-speaking locations]

    def checkForSquare(highwayNameList):
    
        matchers = ['Platz','platz']
    
        # Yup this is very 'pythonic' ... I speak pythonic now!! Jk I stole it from the internet

        return [s for s in highwayNameList if any(xs in s for xs in matchers)] != []

    ### This function targets a situation that was observed at Gierkeplatz in Berlin-Charlottenburg:
    ### here one too many junctions was merged into a cluster constituting a square; 
    ### this case can be described as a junction sharing only one distinct highway with a 
    ### cluster that contains a square; however that one shared highway is not the square described
    ### by the cluster.

    def gierkePlatzSituation(rowHighways, clusterHighways, sharedHighways):
    
        # (1) The cluster contains a square.
        
        if checkForSquare(clusterHighways):
            
        # (2) rowHighways and (clusterHighways - rowhighways) only share one element.
        
            if len(sharedHighways) == 1:
        
        # (3) If the previous two conditions are met and the one additional highway contained in
        #     sharedHighways is not a square, unmerge.
        
                if not checkForSquare(sharedHighways):
            
                    return True
        
        return False

    #### Finally, this function uses all the data and functionality defined above to determine 
    #### where we need to un-merge.

    def rowsToUnmerge(clusterHighwayTypes, clusterHighwayNames, clusterSize, rowHighwayNames):
        
        # Subtract the current row's (junction's) list of associated highways from the ones in the
        # cluster the row (junction) belongs to WHILE BOTH MAY STILL CONTAIN DUPLICATES!! 
        # Logic behind this: we want to find out which elements rowhighways and clusterhighways truly
        # have in common (if we didn't do this subtraction first all of the highways in rowhighways
        # would be included in clusterhighways)

        res = list((Counter(clusterHighwayNames) - Counter(rowHighwayNames)).elements())
                
        # Use this neat set operation to remove duplicates

        noDupsRes = list(set(res))

        sharedHighways = list(set([value for value in rowHighwayNames if value in noDupsRes]))

        # Don't unmerge if the row (junction) shares more than one highway with the cluster.

        if len(sharedHighways) >= 2:

            return False

        # Don't unmerge if we're dealing with a small cluster.

        elif clusterSize <= 3:

            return False

        # Don't unmerge if we're dealing with a junction located at a very large highway:

        elif largeHighwayJunction(clusterHighwayTypes, clusterSize):

            return False

        elif gierkePlatzSituation(rowHighwayNames, clusterHighwayNames, sharedHighways):

            return True

        else:

            return False

    ## b) Now apply all of the stuff defined in a).

    clusterHighwayTypes = nonIsolatedJunctions['neighbour_cluster'].map(highwaysPerClusterDict.get('highwaytypes', {}).get)

    clusterHighwayNames = nonIsolatedJunctions['neighbour_cluster'].map(highwaysPerClusterDict.get('highwaynames', {}).get)

    clusterSizes = nonIsolatedJunctions['neighbour_cluster'].map(membersPerCluster.get)
    rowHighwayNames = nonIsolatedJunctions['highwaynames']

    nonIsolatedJunctions.loc[:,'unmerge'] = np.vectorize(rowsToUnmerge)(clusterHighwayTypes,clusterHighwayNames,clusterSizes,rowHighwayNames)

    ### unmergeFPs = unmerge false positives

    def unmergeFPs(df):

        nextCluster = (df['neighbour_cluster'].max() + 1)
        
        for ind in df.index:
            
            if df.at[ind,'unmerge'] == True:
                
                df.at[ind,'neighbour_cluster'] = nextCluster
                
                nextCluster += 1
                
            else:
                
                continue

    unmergeFPs(nonIsolatedJunctions)

    nonIsolatedJunctions = nonIsolatedJunctions.drop("unmerge",axis=1)

    return nonIsolatedJunctions

#*******************************************************************************************************************
# (X) Call all the functions required for clustering in logical order.

def cluster (region, junctionsdf):

    sortingParams = utils.paramDict[region]["sorting_params"]

    # I.) Determine which junctions have neighbours and which do not 

    junctionsdf = neighbourFindingWrapper(sortByLocation(junctionsdf, sortingParams))

    # II.) Split the df according to 'junction has/does not have neighbours'

    nonIsolatedJunctions, isolatedJunctions = splitDf(junctionsdf)

    # III.) Cluster the nonIsolatedJunctions

    nonIsolatedJunctions = clusterNeighbours(nonIsolatedJunctions)

    # IV.) Separate undesired merges

    nonIsolatedJunctions = clusterCorrection(nonIsolatedJunctions)

    # V.) Add a cluster to the isolated junctions too (each will have their own, due to their isolation :'( ))

    max_ni_clust = nonIsolatedJunctions['neighbour_cluster'].max() 

    isolatedJunctions["neighbour_cluster"] = isolatedJunctions.index.map(lambda x: max_ni_clust + x)

    return nonIsolatedJunctions, isolatedJunctions



    




    