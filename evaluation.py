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
        available_date_origin = dataframes["TRO"].loc[dataframes["TRO"]['ID(long)'] == key, 'AvailableDateOrigin'].values[0]
        car_finished_transport = last_element["TimeSlotDate"] + timedelta(hours=int(last_element["LeadTimeHours"]))

        if not due_date_destination == "-":
            if car_finished_transport > due_date_destination:
                costs += 100
                # additional delay penalty per day: 25e
                time_difference = car_finished_transport - due_date_destination
                number_of_days_delayed = time_difference.days
                costs += 25 * number_of_days_delayed
        else:
            costs += (car_finished_transport - available_date_origin).days
        # additional delay penalty if a car takes longer than its double net transportation time, i.e. transport time without waiting times to arrive #at the
        #customer: 5e
        # TODO: compute of net transportation time has to be changed!
        # Monja: "man berechnet den kürzesten weg (das ist ja nicht schwer) und dessen net transport time und nimmt die dann als referenz. das heißt für alle autos mit dem selben start und zielknoten ist dieser referenzwert gleich"
        double_transportation_time = timedelta(hours=int(2 * sum([el["LeadTimeHours"] for el in val])))
        if car_finished_transport - available_date_origin > double_transportation_time:
            costs += 5 
    return costs
