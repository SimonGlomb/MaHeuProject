from datetime import timedelta

# TODO, vorallem über format von path_segment_dict sprechen
# brauchen irgendetwas um zu gucken wieviele kapazitäten gebucht wurden
# Aktuell: der code und das datum dienen als unique identifier
def compute_costs_of_mapping(car_to_path_segment_mapping, path_segment_dict, dataframes):
    costs = 0
    # one-time delay penalty: 100e
    for key, val in car_to_path_segment_mapping.items():
        last_element = val[-1]
        due_date_destination = dataframes["TRO"].loc[dataframes["TRO"]['ID(long)'] == key, 'DueDateDestinaton'].values[0]

        car_finished_transport = last_element["TimeSlotDate"] + timedelta(hours=int(last_element["LeadTimeHours"]))
        if not due_date_destination == "-":
            if car_finished_transport > due_date_destination:
                costs += 100
                # additional delay penalty per day: 25e
                time_difference = car_finished_transport - due_date_destination
                number_of_days_delayed = time_difference.days
                costs += 25 * number_of_days_delayed
        # additional delay penalty if a car takes longer than its double net transportation time, i.e. transport time without waiting times to arrive #at the
        #customer: 5e
        double_transportation_time = timedelta(hours=int(2 * sum([el["LeadTimeHours"] for el in val])))
        available_date_origin = dataframes["TRO"].loc[dataframes["TRO"]['ID(long)'] == key, 'AvailableDateOrigin'].values[0]
        if car_finished_transport - available_date_origin > double_transportation_time:
            costs += 5 
    # cost per unused transportation capacity unit: 50e
    for key in path_segment_dict:
        capacity = dataframes["PTR"].loc[(dataframes["PTR"]["PathSegmentCode"] == key[0]) & (dataframes["PTR"]["TimeSlotDate"] == key[1]), "Capacity"].values[0]

        capacity_after_booking = path_segment_dict[key[0], key[1]]["Capacity"]
        capacity_unused = capacity - capacity_after_booking
        if capacity_unused > 0 and capacity != capacity_after_booking:
            costs += 50 * capacity_unused
    return costs
