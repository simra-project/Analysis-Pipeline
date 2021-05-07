#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import requests
import json
import time
import os
import datetime
import sys
import argparse
import time

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

    file_name = f"{region}_junctions_buffer={buffer_size}"

    path = utils.getSubDirPath(file_name, "pickled_data")

    # Write data frame to pickle folder; include buffer_size in the file name
    # ==> purpose of this is to be able to reuse data in the manual merging
    #     tool so if a data set for a specific region and buffer size already
    #     exists it can be utilized rather than computing everything from scratch again

    completeJunctions.to_pickle(path)

    return completeJunctions

if __name__ == "__main__":

    # Create the argument parser and add arguments

    parser = argparse.ArgumentParser()

    parser.add_argument(dest='region', type=str, help="The region to compute junctions for.")

    parser.add_argument(dest='buf_size', type=int, help="By how much the one-dimensional junction points will be buffered.")

    # Parse the input parameters

    args = parser.parse_args()

    start_time = time.time()

    completeJunctions = main(args.region, args.buf_size)

    print("--- %s seconds ---" % (time.time() - start_time))

    file_name = f"{args.region}_junctions_complete_{datetime.date.today()}.csv"

    path = utils.getSubDirPath(file_name, "csv_data")

    completeJunctions.to_csv(path, index=False, sep="|")

