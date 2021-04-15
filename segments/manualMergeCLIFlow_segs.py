
# EXTERNAL IMPORTS

import datetime

# INTERNAL IMPORTS

import manualMergePrep_segs

import manualMergeTool_segs

import utils_segs as utils

# ****************************************************************************

print("\nWelcome to the manual merging tool for segments!\n")

# (1) In order to run 'manualMergePrep.py', ask the user for three params:
# * region

region = input ("Please enter a region (in lowercase, e.g.: bern): \n")

print(f'\nThanks! The region you entered is {region}.\n')

# * the other two params (small_buf, large_buf) are optional - ask user if
#   defaults (found in paramDict in utils) should be accepted or custom
#   values desired

small_buf = utils.paramDict[region]["small_buf_default"]

large_buf = utils.paramDict[region]["large_buf_default"]

print(f"The default buffer sizes to compare for this region are: \n")

print(f"Small buffer: {small_buf}")

print(f"Large buffer: {large_buf}")

default = input ("Would you like to accept these defaults? Please reply with yes or no.\n")

if (default == "No"): 

    print("Thanks! You have chosen to supply custom values for a small and large buffer.\n")

    # * read small_buf from user input

    small_buf = float(input("Please enter a rather small buffer size (e.g.: 1): \n"))

    print(f'\nThanks! The small buffer size you entered is {small_buf}.\n')

    # * read large_buf from user input

    large_buf = float(input("Please enter a larger buffer size (e.g.: 1.25): \n"))

    print(f'\nThanks! The large buffer size you entered is {large_buf}. \n')

elif (default == "Yes"):

    print("Thanks! You have chosen to accept the default values for a small and large buffer.\n")

# (2) run 'manualMergePrep.py' - notify user that this will take loooooooong

print("Please be patient as the ensuing computations will take a few moments (up to a few minutes) to complete .........\n")

manualMergePrep_segs.meta_assist(region, small_buf, large_buf)

# (3) Tell the user which outputs were produced and what they will be used for.
#     Specifically, point out the location of the .html map that was generated,
#     as it constitutes the basis for determining where re-merges shall take place.

print("Thanks for waiting! All the data necessary to manually edit junction clusters has been computed.\n")

print(f'Please navigate to directory PyPipeline_/segments and open the file \'{region}-segs-manualClust_{datetime.date.today()}.html\' in your browser. \n')

print('By default, the more conservative clustering solutions (green shapes on the map) will be accepted. \n')

# NEW 13/02/21: Allow not only chosing liberal buffer solutions over conservative ones, but also the deletion
#               of conservative clusters 
#               REMARK: the deletion of more liberal clusters is not necessary as they are only added to the
#                       modified data frame if specifically desired by the user 
#                       (i.e., if a liberal cluster is chosen as a replacement for a conservative one).

# (4) Ask the user if any editing is desired. 

continue_editing = input ("Would you like to perform any modifications? Please reply with yes or no. \n")

while (continue_editing == 'yes'):

    # Repeat steps (5) - (9) while the user wishes to continue editing.

    # (5) Request which operation the user wants to perform.

    desired_operation = input ("Would you like to delete or replace conservative clusters (= green shapes)? Please reply with delete or replace. \n")

    if desired_operation == "delete":

        # (6.a) In order to run 'manualMergeTool_segs.py' > delete_clust, ask the user to provide the cluster to be 
        #       deleted.

        small_buf_clstr_to_delete = float(input("Please provide the cluster ID of the green shape you want to delete (e.g., 43.0). \n"))

        print(f"Thank you! The following green shapes will be replaced: {small_buf_clstr_to_delete}")

        # * region: already asked for above

        # (7.b) run 'manualMergeTool.py' > delete_clust 

        print("Please be patient as the ensuing computations will take a few moments to complete .........\n")

        manualMergeTool_segs.delete_clust(small_buf_clstr_to_delete, region)

        # (8) Tell the user to refresh the map to see the result    

        print(f'Please refresh the map (PyPipeline_/segments/\'{region}-segs-manualClust_{datetime.date.today()}.html\') to see the result.\n')

        # (9) Ask if more manual editing is desired - if so, repeat the process from (5); if not proceed to (9)

        continue_editing = input ("Would you like to continue editing? Please reply with yes or no. \n")

    elif desired_operation == "replace":

        print("Typically, a more conservative clustering solution that should be replaced by a more liberal one consists of multiple green shapes.\n")

        print("You will therefore be prompted to provide the cluster numbers of all those green shapes one by one.\n")

        # (6.b) In order to run 'manualMergeTool.py' > update_clust, ask the user for three params: 
        # * small_buf_clstrs (list of floats) --> ask for them one by one.

        small_buf_clstrs = []
        
        first_small_clstr = float(input("Please enter cluster number of the first green shape you want to replace (e.g., 889.0).\n"))

        small_buf_clstrs.append(first_small_clstr)

        further_small_clstrs = input ("Are there more green shapes you wish to replace? Please reply with yes or no.\n")

        while (further_small_clstrs == 'yes'):

            next_small_clstr = float(input("Please enter the cluster number of the next green shape you want to replace (e.g., 2364.0).\n"))

            small_buf_clstrs.append(next_small_clstr)

            further_small_clstrs = input ("Are there more green shapes you wish to replace? Please reply with yes or no.\n")

        # * large_buf_clstr (float)

        print("Thank you! The following green shapes will be replaced: ")

        for clust in small_buf_clstrs: 

            print(clust)

        print("\nTypically, the more liberal solution to replace the more conservative one will consist of one blue shape only.\n")

        large_buf_clstr = float(input("Please enter the cluster number of the blue shape with which you want to replace the previously specified green ones.\n"))

        print(f'\nThanks! The cluster {large_buf_clstr} will replace the previously specified green clusters.\n')

        # * region: already asked for above

        # (7) run 'manualMergeTool.py' > update_clust 

        print("Please be patient as the ensuing computations will take a few moments to complete .........\n")

        manualMergeTool_segs.update_clust(small_buf_clstrs, large_buf_clstr, region)

        # (8) Tell the user to refresh the map to see the result    

        print(f'Please refresh the map (PyPipeline_/segments/\'{region}-segs-manualClust_{datetime.date.today()}.html\') to see the result (in orange).\n')

        # (9) Ask if more manual editing is desired - if so, repeat the process from (5); if not proceed to (9)

        continue_editing = input ("Would you like to continue editing? Please reply with yes or no. \n")

# (10) Write the resultant data frame to memory: 'manualMergeTool.py' > save_result

print("You've chosen to finish editing. The resultant data will be written to csv.\n")

manualMergeTool_segs.save_result(region)

print(f'Your data can be found here: PyPipeline_/segments/manual_merging_res_{region}_{datetime.date.today()}.csv')