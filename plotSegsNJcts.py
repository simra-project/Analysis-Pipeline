
import sys

sys.path.insert(0, './junctions')
sys.path.insert(0, './segments')

import OSM_jcts
import OSM_segs

import datetime

import os

def getSubDirPath (file_):

    # Concatenate path using os library so system can tell which part of the
    # path is a directory and which is a file name.

    curr_dir = os.path.abspath(os.path.dirname(__file__))

    file_path = os.path.join(curr_dir, 'debug', file_)

    return file_path

# Execute segs script

completeSegs, segMap = OSM_segs.main("hannover",1)

# Save segs csv

file_name_segs = f"hannover_segments_complete_{datetime.date.today()}.csv"

path_segs = getSubDirPath(file_name_segs)

completeSegs.to_csv(path_segs, index=False, sep="|")

# Execute jcts script

completeJunctions, totalMap = OSM_jcts.main("hannover",2, segMap)

# Save jcts csv

file_name_jcts = f"hannover_junctions_complete_{datetime.date.today()}.csv"

path_jcts = getSubDirPath(file_name_jcts)

completeJunctions.to_csv(path_jcts, index=False, sep="|")

# Save jcts map

file_name_map = f'hannover-segs-jcts_{datetime.date.today()}.html'

map_path = getSubDirPath(file_name_map)

totalMap.save(map_path)



