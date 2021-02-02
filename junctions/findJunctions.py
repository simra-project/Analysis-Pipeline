import pandas as pd

from itertools import starmap

from shapely.geometry import Polygon

from shapely.geometry import Point

import os

import utils # internal import

relevantTypes = ['primary','secondary','secondary_link','tertiary','tertiary_link','living_street','residential']

# ********************************************************************************************************************
# (*) Find out which nodes in the nodesdf are junctions.

def identifyjunction(highwayIDs, highwaytypes, highwaynames):
    
    # The node belongs to less than 2 highways and therefore definitely is not a junction;
    # exit
    
    if len(list(set(highwayIDs))) < 2:
        
        return 'no_junction'
    
    else:
           
    # We got more than 2 highways for this junction; put highwaytypes & highwaynames
    # into a nested dict (Python equivalent to a Map) with highwayids as keys
    # Structure of dict vals: tuple of the form (highwaytype, highwayname)
        
        highwayDict = dict(zip(highwayIDs, zip(highwaytypes, highwaynames)))
        
    # Filter according to highwaytype (first element in each value tuple).
        
        # filteredDict = dict(filter(lambda elem: elem[1][0] in relevantTypes, highwayDict.items()))
        
    # Extract highwaynames from the nested dict (second element in each value tuple)
        
        # hwNames = list((v[1] for k, v in filteredDict.items()))

        hwNames = list((v[1] for k, v in highwayDict.items()))

        hwTypes = list((v[0] for k, v in highwayDict.items()))
        
    # Check for duplicated highwaynames by converting to set and then back to list.
        
        if len((list(set(hwNames)))) >= 2:

            if len([hwt for hwt in hwTypes if hwt in relevantTypes]) >= 2:
            
                return 'large_junction'

            else:
                
                return 'small_junction'
        
        else: 
            
            return 'no_junction'

# ********************************************************************************************************************
# (*) Call all the functions in this script in logical order.

def getJunctionsDf(nodesdf, region):

    nodesdf.loc[:,'junction'] = [x for x in starmap(identifyjunction, list(zip(nodesdf['highwayids'],nodesdf['highwaytypes'],nodesdf['highwaynames'])))]

    # jcts = ['small_junction','large_junction']

    junctionsdf = nodesdf[nodesdf['junction'] != 'no_junction']

    junctionsdf.reset_index(inplace=True)

    junctionsdf = junctionsdf.drop('index',axis=1)

    # Find out if we're operating in 'junctions'-subdirectory or its parent directory,
    # PyPipeline_ (background: we want to write all files related to junctions toxs the
    # junctions subdirectory)

    cwd = os.getcwd()

    in_target_dir = utils.inTargetDir(cwd)

    file_name = f"{region}_junctions_for_segs.csv"

    path = file_name if in_target_dir else utils.getSubDirPath(file_name)

    # Keep the column containing information on the type of junction (small vs. large)

    pd.DataFrame(junctionsdf[['junction','id','lat','lon','highwaynames']]).to_csv(path)

    # Now we can get rid of the smaller junctions (only needed in the segments project so
    # it needs to be contained in the 'junctions_for_segs'-df)

    junctionsdf = junctionsdf[junctionsdf['junction'] == 'large_junction']

    junctionsdf.reset_index(inplace=True)

    junctionsdf = junctionsdf.drop(['index','junction'],axis=1)

    # Map ids to list to facilitate cluster comparison in manualClusterPrep
    # COMMENT OUT TO PREVENT THIS

    junctionsdf['id'] = junctionsdf['id'].map(lambda i: [i])

    return junctionsdf