from parse_txt import parse_file
import pandas as pd

dataframes = parse_file('./data/inst001.txt')

# Wir vernachlässigen die kapazität der knoten; wäre in #STE "Capacity" zu finden
dataframes["PTH"] = dataframes["PTH"].filter(["PathOriginCode", "PathDestinationCode", "PathCode"])
dataframes["PTHSG"] = dataframes["PTHSG"].filter(["PathCode", "SegmentCode", "SegmentOriginCode", "SegmentDestinationCode"])
dataframes["SEG"] = dataframes["SEG"].filter(["Code", "OriginCode", "DestinationCode"])
dataframes["PTR"] = dataframes["PTR"].filter(["PathSegmentCode", "TimeSlotDate", "Capacity", "LeadTimeHours"])
# define an explicit ID to assess the PlannedTransport uniquely (instead of by TimeSlotDate or something)
dataframes["PTR"]['ID'] = range(1, len(dataframes["PTR"]) + 1)
dataframes["TRO"] = dataframes["TRO"].filter(["ID(long)", "OriginCode", "DestinationCode", "AvailableDateOrigin", "DesignatedPathCode", "DueDateDestinaton"])

# Merge all the things which i have marked green and purple in my notes: which can be found in OneNote
## inner join to find the cars which fit the origin and destination of paths
result = pd.merge(dataframes["TRO"], dataframes["PTH"], left_on=['OriginCode', 'DestinationCode', "DesignatedPathCode"], right_on=['PathOriginCode', "PathDestinationCode", "PathCode"], how='inner', suffixes=("_TRO", "_PTH"))
## right join, so that we get the path segments which bring the car to the right destination from the right source of the overall path
## right join to get ALL the relevant segments
## in this example only 2 path segments exist, so the table is multiplied by 2
result = pd.merge(result, dataframes["PTHSG"], left_on=["DesignatedPathCode"], right_on=["PathCode"], how="right")
### UNTIL HERE IM VERY CONFIDENT OF CORRECTNESS

# with the following right join we get all possible paths
# number of rows goes from 100 to 900: does make sense in a way as we have 18 plannedtransports but each of them maps to one of the 2 edges (i.e. to one pathsegment), i.e. divided by 2 (if we would have 3 edges, we would divide by 3 etc.). So thats why 18/2 = 9 factor multiplied
result = pd.merge(result, dataframes["PTR"], left_on='SegmentCode', right_on='PathSegmentCode', how='right')
