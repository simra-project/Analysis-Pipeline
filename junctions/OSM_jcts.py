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

import utils
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

def main(region, buffer_size):

    nodesdf = dfShizzle.metaFunc(utils.paramDict[region]["bounding_box"])

    junctionsdf = findJunctions.getJunctionsDf(nodesdf, region)

    bufferedJunctionsDf = bufferJcts.bufferize(junctionsdf, buffer_size)

    nonIsolatedJunctions, isolatedJunctions = clusterJcts.cluster(bufferedJunctionsDf, utils.paramDict[region]["neighbour_param"], utils.paramDict[region]["sorting_params"])

    completeJunctions = tidyData_Jcts.tidyItUp(region, utils.paramDict[region]["centroid"], nonIsolatedJunctions, isolatedJunctions, buffer_size, utils.paramDict[region]["sorting_params"])

    # Write to pickle for future use

    # Find out if we're operating in 'junctions'-subdirectory or its parent directory,
    # PyPipeline_ (background: we want to write all files related to junctions to the
    # junctions subdirectory)

    cwd = os.getcwd()

    in_target_dir = utils.inTargetDir(cwd)

    file_name = f"{region}_junctions_buffer={buffer_size}"

    path = utils.getSubDirPath(file_name, 'pickled_data') if in_target_dir else utils.getPicklePath(file_name)

    # Write data frame to pickle folder; include buffer_size in the file name
    # ==> purpose of this is to be able to reuse data in the manual merging
    #     tool so if a data set for a specific region and buffer size already
    #     exists it can be utilized rather than computing everything from scratch again

    completeJunctions.to_pickle(path)

    return completeJunctions

if __name__ == "__main__":

    completeJunctions = main("hannover",2)

    # Find out if we're operating in 'junctions'-subdirectory or its parent directory,
    # PyPipeline_ (background: we want to write all files related to junctions to the
    # junctions subdirectory)

    cwd = os.getcwd()

    in_target_dir = utils.inTargetDir(cwd)

    file_name = f"hannover_junctions_complete_{datetime.date.today()}.csv"

    path = file_name if in_target_dir else utils.getSubDirPath(file_name)

    completeJunctions.to_csv(path, index=False, sep="|")

