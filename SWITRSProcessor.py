# --------------------------------
# Name: SWITRSProcessor.py
# Purpose: This script is intended to summarize input parties and victims level SWITRS data (CA) to the collision point
# file level in order to provide an enhanced collision dataset (CSV).
# Current Owner: David Wasserman
# Last Modified: 7/16/2017
# Copyright:   (c) CoAdapt
# --------------------------------
# Copyright 2016 David J. Wasserman
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# --------------------------------

# Import Modules
import os, collections
import numpy as np
import pandas as pd

# Define input parameters

output_csv = r"data/related_collisions.csv"
collisions = r"data/Collisions.csv"
parties = r"data/Parties.csv"
victims = r"data/Victims.csv"


# Function Definitions
def func_report(function=None, reportBool=False):
    """This decorator function is designed to be used as a wrapper with other functions to enable basic try and except
     reporting (if function fails it will report the name of the function that failed and its arguments. If a report
      boolean is true the function will report inputs and outputs of a function.-David Wasserman"""

    def func_report_decorator(function):
        def func_wrapper(*args, **kwargs):
            try:
                func_result = function(*args, **kwargs)
                if reportBool:
                    print("Function:{0}".format(str(function.__name__)))
                    print("     Input(s):{0}".format(str(args)))
                    print("     Ouput(s):{0}".format(str(func_result)))
                return func_result
            except Exception as e:
                print(
                    "{0} - function failed -|- Function arguments were:{1}.".format(str(function.__name__), str(args)))
                print(e.args[0])

        return func_wrapper

    if not function:  # User passed in a bool argument
        def waiting_for_function(function):
            return func_report_decorator(function)

        return waiting_for_function
    else:
        return func_report_decorator(function)


@func_report
def unique_stats_agg_prep(dataframe, column, ignore_na=True, stats_type="sum"):
    """This function will return a new dataframe with columns appended to the end that has new columns for every unique
    value in a selected column being flagged with a 1 if that value appears. Alphanumeric characters are the only ones
     accepted as unique values, only special character strings are filtered. It is intended to create fields for
    an aggregation function. In addition to the returned dataframe this function returns a series of tuples in the form
    of [(newuniquefield1,(stats_type),...]. This function is only slightly different from pd.get_dummies()
    params:
    dataframe (pandas dataframe): incoming dataframe where the column with unique values will have fields added to end.
    column (string): column in dataframe that will have its unique values added as fields with 1 when present.
    ignore_na(bool): will ignore na values when creating new fields.
    stats_type (string): the assumed stats string added to the list with a tuple.
    returns:
    dataframe,list of form [(newuniquefield1,(stats_type),...]"""
    series = dataframe[column]
    unique_values = [i for i in series.unique() if ''.join(e for e in str(i) if e.isalnum())]
    if ignore_na:
        unique_values = [i for i in unique_values if not pd.isnull(i)]  # ignore na-values
    preagg_list = []
    for unique_value in unique_values:
        new_name = "F_" + str(unique_value) + "_" + str(column)
        dataframe[new_name] = np.where(dataframe[column] == unique_value, 1, np.NaN)
        preagg_list.append((new_name, (stats_type)))
    return dataframe, preagg_list


def summarize_switrs(output_collision_csv, collisions_csv, victims_csv=None, parties_csv=None):
    """This function will create an enhanced collisions dataframe based on input collisions,victims, and parties
    csv files from SWITRS collision data. The string fields used are constants based on the field schema established
    by SWITRS."""
    try:
        # Define Field Constants
        X_Field = "POINT_X"
        Y_Field = "POINT_Y"
        Case_ID = "CASEID"
        # Start Analysis
        print("Creating dataframes from parties and victims csv...")
        collisions_df = pd.read_csv(collisions_csv, sep=",")
        parties_df = pd.read_csv(parties, sep=",")
        victims_df = pd.read_csv(victims, sep=",")
        print("Gathering victim statistics by case id...")
        victims_df["AvgVAGE"] = victims_df["VAGE"]
        victims_df["VAGE_Minor"] = np.where(victims_df["VAGE"] < 16, 1, np.NaN)
        victims_df["VAGE_Working"]= np.where((victims_df["VAGE"] >=16) & (victims_df["VAGE"] <65),1,np.NaN)
        victims_df["VAGE_Senior"] = np.where(victims_df["VAGE"] >= 65, 1, np.NaN)
        victims_df["MobilLimAge"] = np.where(victims_df["VAGE"] < 16, 1, victims_df["VAGE_Senior"])
        victims_df, victims_sex_stats = unique_stats_agg_prep(victims_df, "VSEX")
        victims_grouped = victims_df.groupby(Case_ID)
        victims_stats = collections.OrderedDict([("AvgVAGE", "mean"), ("VAGE_Minor", "sum"),("VAGE_Working","sum"),
                                                 ("VAGE_Senior", "sum"), ("MobilLimAge", "sum")] + victims_sex_stats)
        victims_stats_df = victims_grouped.agg(victims_stats)
        print("Extending victims statistics to collisions dataframe...")
        collisions_df = pd.merge(collisions_df.reset_index(), victims_stats_df.reset_index(), on=[Case_ID])
        print("Gathering parties statistics by case id...")
        parties_df, parties_movement_stats = unique_stats_agg_prep(parties_df, "MOVEMENT")
        parties_df, parties_vehtype_stats = unique_stats_agg_prep(parties_df, "VEHTYPE")
        parties_df, parties_race_stats = unique_stats_agg_prep(parties_df, "PRACE")
        parties_grouped = parties_df.groupby(Case_ID)
        parties_stats = collections.OrderedDict(parties_race_stats + parties_movement_stats + parties_vehtype_stats)
        parties_stats_df = parties_grouped.agg(parties_stats)
        print("Extending parties statistics to collisions dataframe...")
        collisions_df = pd.merge(collisions_df.reset_index(), parties_stats_df.reset_index(), on=[Case_ID])
        print("Classifying collisions by most vulnerable mode...")
        collisions_df["PrimeModeClass"] = np.where(collisions_df["BICCOL"] == "Y", "Bicycle", None)
        collisions_df["PrimeModeClass"] = np.where(collisions_df["PEDCOL"] == "Y", "Pedestrian",
                                                   collisions_df["PrimeModeClass"])
        collisions_df["PrimeModeClass"] = collisions_df["PrimeModeClass"].fillna(value="Motor Vehicle")
        print("Exporting to csv.")
        collisions_df.to_csv(output_collision_csv)
        print("Returning dataframe.")
        return collisions_df
    except Exception as e:
        print(e.args[0])


# End do_analysis function

# This test allows the script to be used from the operating
# system command prompt (stand-alone), in a Python IDE,
# as a geoprocessing script tool, or as a module imported in
# another script
if __name__ == '__main__':
    summarize_switrs(output_csv, collisions, victims, parties)
