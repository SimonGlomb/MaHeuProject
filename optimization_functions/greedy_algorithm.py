from datetime import timedelta
import pandas as pd
from typing import Tuple

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

# TODO: gucken ob lücke entstehen kann
    def has_path_from_origin_to_destination(id: int, car_to_path_segment_mapping: dict):
        have_origin_match = False
        have_destination_match = False
        if car_to_path_segment_mapping[id]:
            origin_code_TRO = dataframes["TRO"].loc[dataframes["TRO"]['ID(long)'] == id, 'OriginCode'].values[0]
            destination_code_TRO = dataframes["TRO"].loc[dataframes["TRO"]['ID(long)'] == id, 'DestinationCode'].values[0]

            for mapping_dict_el in car_to_path_segment_mapping[id]:
                origin_code_SEG = dataframes["SEG"].loc[dataframes["SEG"]['Code'] == mapping_dict_el["PathSegmentCode"], 'OriginCode'].values[0]
                destination_code_SEG = dataframes["SEG"].loc[dataframes["SEG"]['Code'] == mapping_dict_el["PathSegmentCode"], 'DestinationCode'].values[0]
                if origin_code_SEG == origin_code_TRO:
                    have_origin_match = True
                if destination_code_SEG == destination_code_TRO:
                    have_destination_match = True
                if have_origin_match and have_destination_match:
                    return True
        return False

    
    # Check if the end of transport is at least the leadtimehours (time to deliver) of the mapping before (if existent) plus 24 hours before timeslotdate (when the transport is available)
    def transport_is_usable(timeslotdate, mapping):
        for el in mapping:
            car_finished_transport_and_next_day = el["TimeSlotDate"] + timedelta(hours=int(el["LeadTimeHours"]) + 24)
            # if it is <= then we are good, because then our new transport is doable as the car is available again
            if car_finished_transport_and_next_day > timeslotdate:
                return False
        return True


    # NOTE: can probably be optimized a lot!
    for _, row in result_sorted.iterrows():
        while not has_path_from_origin_to_destination(row["ID(long)"], car_to_path_segment_mapping):
            for _, row in result_sorted.iterrows():
                dict_element = path_segment_dict[row['PathSegmentCode'], row['TimeSlotDate']]
                # first condition checks if list is empty
                # second condition checks if we already have that segment
                if int(dict_element["Capacity"]) > 0:
                    if not car_to_path_segment_mapping[row["ID(long)"]] or (not any(el["PathSegmentCode"] == row["PathSegmentCode"] for el in car_to_path_segment_mapping[row["ID(long)"]]) and transport_is_usable(row["TimeSlotDate"], car_to_path_segment_mapping[row["ID(long)"]])):
                        car_to_path_segment_mapping[row["ID(long)"]].append({"PathSegmentCode": row["PathSegmentCode"], "TimeSlotDate": row["TimeSlotDate"], "LeadTimeHours": dict_element["LeadTimeHours"]})
                        dict_element["Capacity"] -= 1
    return car_to_path_segment_mapping
    #Greedy:
    #1) sortiere nach Deadline (und oder fertigstellungsdatum)
    #2) ordne strecken zu: a) mit frühester ankunft
    #                                          b) kleinsten kosten
    #                                          c) random mit frühesten freine slots