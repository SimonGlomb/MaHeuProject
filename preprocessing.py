from parse_txt import parse_file
import pandas as pd
from datetime import datetime

def convert_to_dataframe(dataframes):
    pd.to_numeric(dataframes["PTR"]["Capacity"], errors='coerce')

    # Wir vernachlässigen die kapazität der knoten; wäre in #STE "Capacity" zu finden
    dataframes["PTH"] = dataframes["PTH"].filter(["PathOriginCode", "PathDestinationCode", "PathCode"])
    dataframes["PTHSG"] = dataframes["PTHSG"].filter(["PathCode", "SegmentCode", "SegmentOriginCode", "SegmentDestinationCode"])
    dataframes["SEG"] = dataframes["SEG"].filter(["Code", "OriginCode", "DestinationCode"])
    dataframes["PTR"] = dataframes["PTR"].filter(["PathSegmentCode", "TimeSlotDate", "Capacity", "LeadTimeHours"])
    # define an explicit ID to assess the PlannedTransport uniquely (instead of by TimeSlotDate or something)
    dataframes["PTR"]['PTR_ID'] = range(1, len(dataframes["PTR"]) + 1)
    dataframes["TRO"] = dataframes["TRO"].filter(["ID(long)", "OriginCode", "DestinationCode", "AvailableDateOrigin", "DesignatedPathCode", "DueDateDestinaton"])

    # TYPE-CASTING
    dataframes["TRO"]['AvailableDateOrigin'] = pd.to_datetime(dataframes["TRO"]['AvailableDateOrigin'], format='%d/%m/%Y-%H:%M:%S')
    dataframes["PTR"]['TimeSlotDate'] = pd.to_datetime(dataframes["PTR"]['TimeSlotDate'], format='%d/%m/%Y-%H:%M:%S')
    dataframes["PTR"]["Capacity"] = pd.to_numeric(dataframes["PTR"]["Capacity"])
    # had some problems with using the pd.to_datetime here, so this will do for now (and it is not a performance bottleneck anyway)
    def handle_dates(date_str):
        if date_str == "-":
            return date_str
        else:
            return datetime.strptime(date_str, '%d/%m/%Y-%H:%M:%S')
    dataframes["TRO"]['DueDateDestinaton'] = dataframes["TRO"]['DueDateDestinaton'].apply(handle_dates)


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

    ### for the non 001 datasets, things like this happened:
    #      ID(long) OriginCode DestinationCode AvailableDateOrigin DesignatedPathCode  ...              PathSegmentCode         TimeSlotDate Capacity LeadTimeHours PTR_ID
    #3510      NaN        NaN             NaN                 NaN                NaN  ...  GER02TERMCZE01DEAL-TRUCK-03  12/03/2024-00:00:00     10.0          48.0     16       
    #3571      NaN        NaN             NaN                 NaN                NaN  ...  GER02TERMCZE01DEAL-TRUCK-03  13/03/2024-00:00:00     10.0          48.0     17       
    #3632      NaN        NaN             NaN                 NaN                NaN  ...  GER02TERMCZE01DEAL-TRUCK-03  14/03/2024-00:00:00     10.0          48.0     18       
    #3693      NaN        NaN             NaN                 NaN                NaN  ...  GER02TERMCZE01DEAL-TRUCK-03  15/03/2024-00:00:00     10.0          48.0     19       
    # After some investigation, it seems safe to drop these rows, as the reason is probably this: using a right join and there are no matching entries in the left DataFrame
    # and most importantly, we have to ID(long) for the car, so we cannot use it for mapping anyway
    result = result.dropna()
    return result

