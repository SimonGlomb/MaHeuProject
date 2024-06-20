from datetime import timedelta

def has_path_without_gaps_from_origin_to_destination(id: int, car_to_path_segment_mapping: dict, dataframes):
    if car_to_path_segment_mapping[id]:
        origin_code_TRO = dataframes["TRO"].loc[dataframes["TRO"]['ID(long)'] == id, 'OriginCode'].values[0]
        destination_code_TRO = dataframes["TRO"].loc[dataframes["TRO"]['ID(long)'] == id, 'DestinationCode'].values[0]
        # for the first iteration, to check if start is fine, initialize it like this:
        last_mapping_dict_el_destination = origin_code_TRO
        # check of the final destination
        last_element_destination = dataframes["SEG"].loc[dataframes["SEG"]['Code'] == car_to_path_segment_mapping[id][-1]["PathSegmentCode"], 'DestinationCode'].values[0]
        if destination_code_TRO != last_element_destination:
            return False
        for mapping_dict_el in car_to_path_segment_mapping[id]:
            origin_code_SEG = dataframes["SEG"].loc[dataframes["SEG"]['Code'] == mapping_dict_el["PathSegmentCode"], 'OriginCode'].values[0]
            # checks if there is a gap
            if last_mapping_dict_el_destination != origin_code_SEG:
                return False
            last_mapping_dict_el_destination = dataframes["SEG"].loc[dataframes["SEG"]['Code'] == mapping_dict_el["PathSegmentCode"], 'DestinationCode'].values[0]
    else:
        return False
    return True

def all_cars_have_path_without_gaps_from_origin_to_destination(car_ids: int, car_to_path_segment_mapping: dict, dataframes):
    return all(has_path_without_gaps_from_origin_to_destination(id, car_to_path_segment_mapping, dataframes) for id in car_ids)


# Check if the end of the transport is at least the leadtimehours (time to deliver) of the transport before (if existent) plus 24 hours before timeslotdate (when the transport is available)
# NOTE: can be optimized
def transport_is_usable(timeslotdate, mapping):
    for el in mapping:
        car_finished_transport_and_next_day = el["TimeSlotDate"] + timedelta(hours=int(el["LeadTimeHours"]) + 24)
        # if it is <= then we are good, because then our new transport is doable as the car is available again
        car_finished_transport_and_next_day = car_finished_transport_and_next_day.replace(hour=0, minute=0, second=0, microsecond=0)
        if car_finished_transport_and_next_day > timeslotdate:
            return False
    return True

def get_dict_to_keep_track_of_capacities(dataframes, result):
    unique_path_segment_codes = result[['PathSegmentCode', 'TimeSlotDate']].drop_duplicates()
    path_segment_dict = {}
    # use my own dict and not read it from the dataframe, because i want to update this dict to keep track of the capacities
    for _, path_segment in unique_path_segment_codes.iterrows():
        mask = (dataframes["PTR"]['PathSegmentCode'] == path_segment['PathSegmentCode']) & (dataframes["PTR"]["TimeSlotDate"] == path_segment['TimeSlotDate'])
        selected_row = dataframes["PTR"][mask]
        path_segment_dict[path_segment['PathSegmentCode'], path_segment['TimeSlotDate']] = {"Capacity": selected_row["Capacity"].astype(float).astype(int).iloc[0], "LeadTimeHours": selected_row["LeadTimeHours"].astype(float).astype(int).iloc[0]}
    return path_segment_dict