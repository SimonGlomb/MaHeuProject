import pandas as pd
from typing import Tuple
import preprocessing

from utility import transport_is_usable, get_dict_to_keep_track_of_capacities, all_cars_have_path_without_gaps_from_origin_to_destination

def apply(dataframes: dict) -> dict:
    result = preprocessing.convert_to_dataframe(dataframes)
    all_ids = dataframes["TRO"]["ID(long)"].unique()
    car_to_path_segment_mapping = {id: [] for id in all_ids}

    path_segment_dict = get_dict_to_keep_track_of_capacities(dataframes=dataframes, result=result)

    result_sorted = result.sort_values(by=['DueDateDestinaton', 'TimeSlotDate', 'AvailableDateOrigin'])

    current_car_position = {id: dataframes["TRO"].loc[dataframes["TRO"]["ID(long)"]==id, "OriginCode"].values[0] for id in all_ids}

    # here, we now take the rows greedy
    for _, row in result_sorted.iterrows():
        dict_element = path_segment_dict[row['PathSegmentCode'], row['TimeSlotDate']]
        # condition checks if PTR is usable
        # condition checks if car has a position (if not, it is already at its destination)
        # condition checks if the car can use the segment from its "current" (dependent on iteration) position
        current_car_id = row["ID(long)"]
        # still capacity on the PTR
        if dict_element["Capacity"] > 0:
            # PTR gives right path for car
            if row["PathOriginCode"] == dataframes["TRO"].loc[dataframes["TRO"]["ID(long)"]==current_car_id, "OriginCode"].values[0] and row["PathDestinationCode"] == dataframes["TRO"].loc[dataframes["TRO"]["ID(long)"]==current_car_id, "DestinationCode"].values[0]:
                #if current_car_id == "444" and row["SegmentOriginCode"] == "GBR01PLANT":
                    #breakpoint()
                    # TODO: 
                if transport_is_usable(row["TimeSlotDate"], car_to_path_segment_mapping[current_car_id]) and current_car_id in current_car_position and current_car_position[current_car_id] == row["SegmentOriginCode"]:
                    # The following outcommented line checks if we already have that segment: not needed!
                    #if not any(el["PathSegmentCode"] == row["PathSegmentCode"] for el in car_to_path_segment_mapping[current_car_id]) 
                    car_to_path_segment_mapping[current_car_id].append({"PathSegmentCode": row["PathSegmentCode"], "TimeSlotDate": row["TimeSlotDate"], "LeadTimeHours": dict_element["LeadTimeHours"]})
                    dict_element["Capacity"] -= 1
                    current_car_position[current_car_id] = row["SegmentDestinationCode"]
                    if current_car_id in current_car_position and current_car_position[current_car_id] == dataframes["TRO"].loc[dataframes["TRO"]["ID(long)"]==current_car_id, "DestinationCode"].values[0]:
                        del current_car_position[current_car_id]
    # TODO: dataframes["TRO"].loc[dataframes["TRO"]["ID(long)"]=="1", "OriginCode"]
    # car_to_path_segment_mapping["1"]
    # endet in TUR01PORTBEL01PORT-VESSEL-02
    # muss aber noch nach CZE01DEAL
    # man könnte jetzt nach gucken ob das überhaupt noch geht
    # bzw macht die leadtimehour mir auch sorgen :[{'PathSegmentCode': 'TUR01PLANTTUR01PORT-TRUCK-01', 'TimeSlotDate': Timestamp('2024-03-13 00:00:00'), 'LeadTimeHours': 12}, {'PathSegmentCode': 'TUR01PORTBEL01PORT-VESSEL-02', 'TimeSlotDate': Timestamp('2024-03-22 00:00:00'), 'LeadTimeHours': 144}]
    # TODO: filtern nach elementen mit länge 2
    # FOLLOWING CODE TO BRING IT TO datetime datatype, but turns out it is not necessary, so i save a lot computation time
    #for id in all_ids:
    #    for path_segment_el in car_to_path_segment_mapping[id]:
    #        path_segment_el["TimeSlotDate"].to_pydatetime()
    return car_to_path_segment_mapping