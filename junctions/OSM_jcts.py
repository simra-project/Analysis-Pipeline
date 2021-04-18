#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import requests
import json
import time
#import concurrent.futures
import os
import datetime

pd.set_option('display.max_columns', 200)

import utils_jcts as utils
import dataAcqAndForm_Jcts as dfShizzle
import findJunctions
import bufferJcts
import clusterJcts
import tidyData_Jcts

# ARGUMENTS.
#  * region: a string - which region are we currently looking at? Required for writing files.
#  * boundingBox: bounding box for region; used for querying data from Overpass API
#  * bbCentroid: the bounding box centroid (a lat/lon pair); required for map creation
#  * neighbourParam: for the purpose of clustering junctions, we sort them by location.
#                    After sorting, it is obvsly not economical to compare every junction to every 
#                    other junction in the df to determine if they're neighbours. Instead, we're only
#                    looking at the x rows above and below each junction. However, this x will be
#                    different for different regions (as the dfs are of different sizes). Hence,
#                    for every region we're trying out different values for this parameter to compare
#                    the results and determine which value is most suitable.
#  * buffer_size: junctions are buffered into two-dimensional shapes according to the mean width of the
#                highways intersecting at this junction multiplied with a factor. This factor varies 
#                depending on the city layout.
#  * sortingParams: either ['lat','lon'] or ['lon','lat']; that's because we're sorting the junctions
#                   by location to make some operations more efficient and it is more sensible to
#                   sort by lat resp. lon first depending on the shape of the bounding box 
#                   (long but slim bounding box: sort by lat first; wide but low bb: sort by lon first) 

def main(region, buffer_size, segMap):

    nodesdf = dfShizzle.metaFunc(utils.paramDict[region]["bounding_box"])

    junctionsdf = findJunctions.getJunctionsDf(nodesdf, region)

    bufferedJunctionsDf = bufferJcts.bufferize(junctionsdf, buffer_size)

    nonIsolatedJunctions, isolatedJunctions = clusterJcts.cluster(bufferedJunctionsDf, utils.paramDict[region]["neighbour_param"], utils.paramDict[region]["sorting_params"])

    completeJunctions, totalMap = tidyData_Jcts.tidyItUp(region, segMap, utils.paramDict[region]["centroid"], nonIsolatedJunctions, isolatedJunctions, buffer_size, utils.paramDict[region]["sorting_params"])

    # Write to pickle for future use

    file_name = f"{region}_junctions_buffer={buffer_size}"

    path = utils.getSubDirPath(file_name, "pickled_data")

    # Write data frame to pickle folder; include buffer_size in the file name
    # ==> purpose of this is to be able to reuse data in the manual merging
    #     tool so if a data set for a specific region and buffer size already
    #     exists it can be utilized rather than computing everything from scratch again

    completeJunctions.to_pickle(path)

    return completeJunctions, totalMap

if __name__ == "__main__":

    completeJunctions = main("bern",2)

    file_name = f"bern_junctions_complete_{datetime.date.today()}.csv"

    path = utils.getSubDirPath(file_name, "csv_data")

    completeJunctions.to_csv(path, index=False, sep="|")

