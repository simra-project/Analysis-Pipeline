
import sys

sys.path.insert(0, './junctions')
sys.path.insert(0, './segments')

import OSM_jcts
import OSM_segs

import utils_segs

import utils_jcts

import datetime

completeSegs, segMap = OSM_segs.main("bern",1)

file_name_segs = f"bern_segments_complete_{datetime.date.today()}.csv"

path_segs = utils_segs.getSubDirPath(file_name_segs, "csv_data")

completeSegs.to_csv(path_segs, index=False, sep="|")

completeJunctions = OSM_jcts.main("bern",2, segMap)

file_name_jcts = f"bern_junctions_complete_{datetime.date.today()}.csv"

path_jcts = utils_jcts.getSubDirPath(file_name_jcts, "csv_data")

completeJunctions.to_csv(path_jcts, index=False, sep="|")

