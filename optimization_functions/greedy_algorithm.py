import pandas as pd
from typing import Tuple

from utility import transport_is_usable, get_dict_to_keep_track_of_capacities, all_cars_have_path_without_gaps_from_origin_to_destination

def apply(result: pd.DataFrame, dataframes: dict) -> dict:
    all_ids = dataframes["TRO"]["ID(long)"].unique()
    car_to_path_segment_mapping = {id: [] for id in all_ids}

    path_segment_dict = get_dict_to_keep_track_of_capacities(dataframes=dataframes, result=result)

    result_sorted = result.sort_values(by=['DueDateDestinaton', 'TimeSlotDate', 'AvailableDateOrigin'])

    current_car_position = {id: dataframes["TRO"]["OriginCode"].values[0] for id in all_ids}

    # here, we now take the rows greedy
    for _, row in result_sorted.iterrows():
        dict_element = path_segment_dict[row['PathSegmentCode'], row['TimeSlotDate']]
        # condition checks if PTR is usable
        # condition checks if car has a position (if not, it is already at its destination)
        # condition checks if the car can use the segment from its "current" (dependent on iteration) position
        current_car_id = row["ID(long)"]
        if dict_element["Capacity"] > 0:
            if transport_is_usable(row["TimeSlotDate"], car_to_path_segment_mapping[current_car_id]) and current_car_id in current_car_position and current_car_position[current_car_id] == row["SegmentOriginCode"]:
                # The following outcommented line checks if we already have that segment: not needed!
                #if not any(el["PathSegmentCode"] == row["PathSegmentCode"] for el in car_to_path_segment_mapping[current_car_id]) 
                car_to_path_segment_mapping[current_car_id].append({"PathSegmentCode": row["PathSegmentCode"], "TimeSlotDate": row["TimeSlotDate"], "LeadTimeHours": dict_element["LeadTimeHours"]})
                dict_element["Capacity"] -= 1
                current_car_position[current_car_id] = row["SegmentDestinationCode"]
                if current_car_id in current_car_position and current_car_position[current_car_id] == dataframes["TRO"].loc[dataframes["TRO"]["ID(long)"]==current_car_id, "DestinationCode"].values[0]:
                    del current_car_position[current_car_id]
    return car_to_path_segment_mapping