from datetime import timedelta
import pandas as pd
from typing import Tuple

from utility import transport_is_usable

def apply(result: pd.DataFrame, dataframes: dict) -> dict:
    all_ids = dataframes["TRO"]["ID(long)"].unique()
    car_to_path_segment_mapping = {id: [] for id in all_ids}

    unique_path_segment_codes = result[['PathSegmentCode', 'TimeSlotDate']].drop_duplicates()
    # to look which capacities already have been booked
    path_segment_dict = {}

    # use my own dict and not read it from the dataframe, because i want to update this dict to keep track of the capacities
    for _, path_segment in unique_path_segment_codes.iterrows():
        mask = (dataframes["PTR"]['PathSegmentCode'] == path_segment['PathSegmentCode']) & (dataframes["PTR"]["TimeSlotDate"] == path_segment['TimeSlotDate'])
        selected_row = dataframes["PTR"][mask]
        path_segment_dict[path_segment['PathSegmentCode'], path_segment['TimeSlotDate']] = {"Capacity": selected_row["Capacity"].astype(float).astype(int).iloc[0], "LeadTimeHours": selected_row["LeadTimeHours"].astype(float).astype(int).iloc[0]}

    result_sorted = result.sort_values(by=['DueDateDestinaton', 'TimeSlotDate', 'AvailableDateOrigin'])

    # here, we now take the rows greedy
    #while not all_cars_have_path_without_gaps_from_origin_to_destination(all_ids, car_to_path_segment_mapping):
    for _, row in result_sorted.iterrows():
        dict_element = path_segment_dict[row['PathSegmentCode'], row['TimeSlotDate']]
        # first condition checks if list is empty
        # second condition checks if we already have that segment
        if dict_element["Capacity"] > 0:
            if not car_to_path_segment_mapping[row["ID(long)"]] or (not any(el["PathSegmentCode"] == row["PathSegmentCode"] for el in car_to_path_segment_mapping[row["ID(long)"]]) and transport_is_usable(row["TimeSlotDate"], car_to_path_segment_mapping[row["ID(long)"]])):
                car_to_path_segment_mapping[row["ID(long)"]].append({"PathSegmentCode": row["PathSegmentCode"], "TimeSlotDate": row["TimeSlotDate"], "LeadTimeHours": dict_element["LeadTimeHours"]})
                dict_element["Capacity"] -= 1
    return car_to_path_segment_mapping
    #Greedy:
    #1) sortiere nach Deadline (und oder fertigstellungsdatum)
    #2) ordne strecken zu: a) mit frühester ankunft
    #                                          b) kleinsten kosten
    #                                          c) random mit frühesten freine slots