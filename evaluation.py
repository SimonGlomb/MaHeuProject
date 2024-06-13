from datetime import timedelta
import pandas as pd

# TODO: car_to_path_segment_mapping als tabelle visualisieren
def compute_costs_of_mapping(car_to_path_segment_mapping, dataframes):
    costs = 0
    one_time_delay_penalty = 0
    additional_delay_penalty = 0
    delay_longer_than_double_net_penalty = 0
    cost_days_without_reaching_destination = 0
    # one-time delay penalty: 100e
    for key, val in car_to_path_segment_mapping.items():
        last_element = val[-1]
        due_date_destination = dataframes["TRO"].loc[dataframes["TRO"]['ID(long)'] == key, 'DueDateDestinaton'].values[0]
        available_date_origin = dataframes["TRO"].loc[dataframes["TRO"]['ID(long)'] == key, 'AvailableDateOrigin'].values[0]
        car_finished_transport = last_element["TimeSlotDate"] + timedelta(hours=int(last_element["LeadTimeHours"]))
        days_delayed = car_finished_transport - available_date_origin

        if not due_date_destination == "-":
            if car_finished_transport > due_date_destination:
                one_time_delay_penalty += 100
                # additional delay penalty per day: 25e
                time_difference = car_finished_transport - due_date_destination
                number_of_days_delayed = time_difference.days
                additional_delay_penalty += 25 * number_of_days_delayed
            # additional delay penalty if a car takes longer than its double net transportation time, i.e. transport time without waiting times to arrive #at the
            #customer: 5e
            # look for the path which the car is taking
            net_transport_time = dataframes["PTH"][(dataframes["PTH"]["PathOriginCode"] == dataframes["TRO"]["OriginCode"].values[0]) & (dataframes["PTH"]["PathDestinationCode"] == dataframes["TRO"]["DestinationCode"].values[0])]["DefaultLeadTimeHours"]
            #for segment in val:
            #    filtered_df = merged_df[merged_df["SegmentCode"] == segment["PathSegmentCode"]]
            #    net_transport_time = dataframes["PTH"][dataframes["PTH"] == filtered_df["PathCode"].values[0]]["DefaultLeadTimeHours"]
            double_transportation_time = timedelta(hours=int(2 * net_transport_time.iloc[0]))
            if car_finished_transport - available_date_origin > double_transportation_time:
                delay_longer_than_double_net_penalty += 5 * days_delayed
        else:
            cost_days_without_reaching_destination += days_delayed.days
    print("One Time Delay Penalty:", one_time_delay_penalty)
    print("Additional Delay Penalty:", additional_delay_penalty)
    print("Delay Longer Than Double Net Penalty:", delay_longer_than_double_net_penalty)
    print("Cost Days Without Reaching Destination:", cost_days_without_reaching_destination)
    costs = one_time_delay_penalty + additional_delay_penalty + delay_longer_than_double_net_penalty + cost_days_without_reaching_destination
    print("Overall Costs:", costs)
    return costs
