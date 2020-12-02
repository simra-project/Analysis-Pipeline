
# External imports

import fire

import pandas as pd

import numpy as np

from itertools import starmap

from shapely.geometry.polygon import Polygon 

# Internal imports

# (1) Manual cluster preparation tool:
#     Provides the data required for manual cluster correction.
#     This data indicates where clustering solutions differ between buffers, i.e. where merges have
#     taken place when utilizing a rather liberal buffer parameter (e.g., 3) but not when utilizing a 
#     more conservative one (e.g., 2).
#     2 and 3 as conservative resp. liberal buffer parameter will work in most cases; consider increasing
#     resp. decreasing them by 0.5 each for particularly narrow resp. wide city layouts.
#     
#     In this script, we do not only use the data generated by manualClusterPrep but also call one of its
#     functions directly:
#     * plotPrep: polygon shapes of junctions in the same cluster are dissolved, i.e. melted together;
#                 the remaining columns are also aggregated by cluster. (Naturally, these operations
#                 are only performed for the 'non-isolated junctions', i.e. those whose polygon surfaces
#                 overlap with those of other junctions) 

import manualClusterPrep

# (2) Mapping tool as helper for manual cluster correction:
#     Differs from the standard mapping tool used by the main script (OSM_Jcts) with respect to the following aspects:
#     - inconsistent clusters (where merges have taken place with a liberal, but not a conservative buffer)
#       are highlighted in yellow.
#     - markers are attached to polygons; upon click, the respective cluster-nr. is displayed. This way,
#       a manual merge can be performed via CLI by specifying the to-be-merged cluster nrs.

import mapJcts_clustAssist as mapping

# (3) Data tidying tool for junctions:
#     This is the exact same script used by the main script (OSM_Jcts). Here, it helps with
#     - dealing with multi-polygons which may have emerged during cluster merges
#     - aligning the columns in the data frame containing non-isolated junctions (which have been clustered and merged
#       together) and isolated junctions (whose polygon surfaces don't overlap with those of any other junctions
#       and which hence have not been merged with any other junctions),
#     - and finally merging the two dfs together. 

import tidyData_Jcts

# Expose functionality as CLI using fire library

# ($) Function for changing a junction's cluster manually via command line.

# Sample call of CLI: python manualMergeTool.py --curr-clust=600.0 --new_clust=605.0 --region="pforz" --buffer_size=2

# USAGE:
# (a) Execute manualClusterPrep, specifying the region and the buffers of different sizes to compare.
# (b) Open the map generated by manualClusterPrep: {region}-jcts-manualClust_{YYY-MM-DD}.html
# (c) Examine which of the inconsistent clusters you want to merge (click on marker reveals the respective neighbour clusters).
# (d) Call update_clust according to the sample call above, putting in as parameters the clusters to merge, the region
#     and the size of the smaller buffer.
# (e) Reload the map (refresh browser window) to see the result.

def update_clust(small_buf_clstrs, large_buf_clstr, region, buffer_size):

    small_buf_inconsist = pd.read_pickle("small_buf_inconsist")

    large_buf_inconsist = pd.read_pickle("large_buf_inconsist")

    consistent_clusters = pd.read_pickle("consistent_clusters")

    # 'small_buf_clstrs' is a list of clusters having emerged in the small_buf-solution; remove the rows
    # corresponding to these clusters from 'small_buf_inconsist' as the large_buf-solution for the same
    # clustering problem is preferred as per user input. Accordingly, RESOLVE the conflict between the
    # small_buf- and large_buf-solutions by deleting the small_buf one and adding the large_buf one to our df 
    # containing the 'consistent_clusters'.

    # Delete the rejected cluster solution from 'small_buf_inconsist'

    for clust in small_buf_clstrs:

        small_buf_inconsist = small_buf_inconsist[small_buf_inconsist['neighbour_cluster'] != clust]

    # Grab the accepted solution from 'large_buf_inconsist'

    accepted_solution = large_buf_inconsist.loc[large_buf_inconsist['neighbour_cluster'] == large_buf_clstr]

    # Set 'neighbour_cluster' to 999999 to make manual editing obvious and facilitate highlighting on map

    accepted_solution['neighbour_cluster'] = 999999

    large_buf_inconsist.loc[large_buf_inconsist['neighbour_cluster'] == large_buf_clstr, ['neighbour_cluster']] = 999999

    # Append accepted solution to 'consistent_clusters'

    consistent_clusters = pd.concat([consistent_clusters, accepted_solution], ignore_index = True, sort = False)

    small_buf_inconsist_nonIsolated, small_buf_inconsist_isolated = manualClusterPrep.splitDf(small_buf_inconsist)

    mapping.runAllMapTasks(region, small_buf_inconsist_nonIsolated, small_buf_inconsist_isolated, large_buf_inconsist, buffer_size)

    # Pickle the three data sets for further editing

    small_buf_inconsist.to_pickle("small_buf_inconsist")

    large_buf_inconsist.to_pickle("large_buf_inconsist")

    consistent_clusters.to_pickle("consistent_clusters")    

    '''

    complete_df = pd.read_pickle("manualMergeTarget")

    complete_df.loc[:,'neighbour_cluster'] = complete_df['neighbour_cluster'].map(lambda x: x if x != curr_clust else new_clust)

    target, remainder = reMerge(complete_df, new_clust)

    # mapping.runAllMapTasks(region, target, remainder, buffer_size)

    complete_df = tidyData_Jcts.explodeAndConcat(target, remainder)

    complete_df.to_pickle("manualMergeTarget")

    complete_df.to_csv('manual_merging_res.csv', index=False, sep="|")

    '''

if __name__ == '__main__':
  fire.Fire(update_clust)


