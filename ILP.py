import parse_txt
import datetime
import pandas as pd
import math
import itertools

from ortools.sat.python import cp_model

from outdated.preprocessing import convert_to_dataframe
import utility
import preprocessing

model = cp_model.CpModel()

# DEFINE SETS
# file_path = "inst002a.txt"
file_path = "inst001.txt"
dataframes = parse_txt.parse_file("./data/" + file_path)
dataframes_type_casted = parse_txt.parse_file("./data/" + file_path)
# call it for the typecasting of dataframes_type_casted etc.
result = convert_to_dataframe(dataframes_type_casted)

# Set of Locations
L = {code for code in dataframes["LOC"]["Code"]}
# Set of cars
A = {id for id in dataframes["TRO"]["ID(long)"]}
# Set of transports
T = {(code, time) for code, time in zip(dataframes_type_casted["PTR"]["PathSegmentCode"], dataframes_type_casted["PTR"]["TimeSlotDate"])}
# Set of segments
# s1 and s2 are pandas series
def return_mask(s1, s2):
    # can use [0] as it is unique for a path
    result = []
    for el in s2:
        result.append(s1[0] == el)
    return pd.Series(result, index=s2.index)


list_of_pathcode = dataframes_type_casted["PTHSG"].groupby('SegmentCode')['PathCode'].apply(list).reset_index()
path_origin_code = dataframes_type_casted["PTH"].groupby("PathCode")["PathOriginCode"].first() # unique, no list needed
path_destination_code = dataframes_type_casted["PTH"].groupby("PathCode")["PathDestinationCode"].first() # unique, no list needed
dataframes_type_casted["PTH"].groupby("PathCode").apply(lambda x: list(set(x))).reset_index()
S = {}
for index, row in dataframes_type_casted["PTHSG"].iterrows():
    segment_code = row["SegmentCode"]
    path_codes = list_of_pathcode.loc[list_of_pathcode['SegmentCode'] == segment_code, "PathCode"].iloc[0], #iloc[0] to unpack out of series
    S[segment_code] = {"OriginCode": row["SegmentOriginCode"], 
                     "DestinationCode": row["SegmentDestinationCode"], 
                     "PathCode": path_codes[0], # [0] to unpack tuple
                     "PathOriginCode": [path_origin_code[path_code].iloc[0] for path_code in path_codes],
                     "PathDestinationCode": [path_destination_code[path_code].iloc[0] for path_code in path_codes],
                     }

# #dataframes_type_casted["PTHSG"].groupby('SegmentCode')['PathCode'].apply(list).reset_index()
# #dataframes_type_casted["PTHSG"].groupby('SegmentCode')['PathCode'].apply(list).apply(lambda x: list(set(x))).reset_index()

def find_first_match(df, segment_e_value, time_value):
    matching_rows = df[(df['PathSegmentCode'] == segment_e_value) & (df['TimeSlotDate'] == time_value)]
    if not matching_rows.empty:
        return matching_rows.iloc[0]
    else:
        return None
    
def get_attribute_of_car(a, name_of_attribute):
    return dataframes_type_casted["TRO"][(dataframes_type_casted["TRO"]['ID(long)'] == a)].iloc[0][name_of_attribute]


# Capacities
C = {(el[0], el[1]): int(float(find_first_match(dataframes_type_casted["PTR"], el[0], el[1])["Capacity"])) for el in T}


# DEFINE VARIABLES

# assignment if car a is assigned to transport s
x = {}
for a in A:
    for t in T:
        x[(a, t)] = model.NewBoolVar(f'x[{a},{t}]')

# CONSTRAINTS

# Capacity is not too much for each transport
for t in T:
    model.Add(sum(x[(a, t)] for a in A) <= C[t])


# ensure that car stays at origin until available date is reached
for a in A:
    for (code, time) in T:
        if time < get_attribute_of_car(a, "AvailableDateOrigin"):
            model.Add(x[(a, (code, time))] == 0)



# check coherence and if segment is also useful to reach final destination, i.e. using a correct path
for a in A:
    # transport is useful for that car is encoded by checking PathCode

    # ensure that we leave the origin: each car takes transport which leads to the right path from the origin
    model.Add(sum(x[(a, (code_t, time_t))] for (code_t, time_t) in T 
                    if get_attribute_of_car(a, "OriginCode") == S[code_t]["OriginCode"] # is the transport from our origin?
                    and get_attribute_of_car(a, "DesignatedPathCode") in S[code_t]["PathCode"]) # is the transport leading of our goal?
                    == 1) # we have to have exactly one of them

    # ensure that we reach the destination of the car
    model.Add(sum(x[(a, (code_t, time_t))] for (code_t, time_t) in T 
                    if get_attribute_of_car(a, "DestinationCode") == S[code_t]["DestinationCode"] 
                    and get_attribute_of_car(a, "DesignatedPathCode") in S[code_t]["PathCode"]) 
                    == 1)

    # Ensure no gaps and the continuity of the path; together with the ensurance that car leaves origin, it finds full path
    # now we can assume that we leave the origin, so we now have to ensure we dont stop somewhere
    for (code_t, time_t) in T:
        # car is not at its goal yet 
        if S[code_t]["DestinationCode"] != get_attribute_of_car(a, "DestinationCode"):
            model.Add(sum(x[(a, (next_code_t, next_time_t))] for (next_code_t, next_time_t) in T
                    if S[code_t]["DestinationCode"] == S[next_code_t]["OriginCode"]  # it really is a next possible transport
                    and get_attribute_of_car(a, "DesignatedPathCode") in S[code_t]["PathCode"] # transport leads on to right destination 
            ) == 1).OnlyEnforceIf(x[(a, (code_t, time_t))]) # then we have to take one of the possible transports

    # transport path is not useful for whole goal of car a reaching its final destination
    for (code_t, time_t) in T:
        # "!=" zu "in" ändern
        if not get_attribute_of_car(a, "DestinationCode") in S[code_t]["PathDestinationCode"]:
            model.Add(x[(a, t)] == 0)

# ensure that we wait at a place leadtimehours and the next day before assigning another transport
for a in A:
    for t1 in T:
        code1, time1 = t1
        LTH = int(float(find_first_match(dataframes_type_casted["PTR"], code1, time1)["LeadTimeHours"]))
        for t2 in T:
            code2, time2 = t2
            # if time2 < (time1 + pd.Timedelta(hours=LTH+24)).replace(hour=0, minute=0, second=0, microsecond=0):
            if time2 < (time1 + pd.Timedelta(hours=LTH+24)).replace(hour=0, minute=0, second=0, microsecond=0):
                #prüfen das die auch nebeneinander sind, und gucken ob auf richtigem pfad
                if S[code1]["DestinationCode"] == S[code2]["OriginCode"]:# and get_attribute_of_car(a, "DestinationCode") == S[code1]["PathDestinationCode"]:
                    model.Add(x[(a, t1)] + x[(a, t2)] <= 1).OnlyEnforceIf(x[(a, (code1, time1))])



cars, paths, segments, eot = preprocessing.construct_instance(dataframes)

#delivery_times = {}
delivery_date_IntVar = {}
for a in A:
    #delivery_times[a] = model.NewIntVar(0, 1000000000, f'delivery_time_{a}')  # Example range in minutes
    delivery_date_IntVar[a] = model.NewIntVar(0, int(pd.Timestamp.max.timestamp()), 'delivery_date_IntVar')

delivery_times = {}
max_time_temp = {}
for a in A:
    departures, assigned_path, current_delivery = utility.assign_timeslots(cars[a], paths, segments, eot)

    for t in T:
        curr_delivery_dates = {}
        curr_max = {}
        code_t, time_t = t
        LTH = int(float(find_first_match(dataframes_type_casted["PTR"], code_t, time_t)["LeadTimeHours"]))

        delivery_date = (time_t + pd.Timedelta(hours=LTH)).replace(hour=0, minute=0, second=0, microsecond=0)
        delivery_times[a, t] = int(float(delivery_date.timestamp())) - 60*60 # TODO: -60*60 ist nur der quickfix um eine stunde abzuziehen, ist wegen timezones passiert das hier eine stunde mehr draufgerechnet wurde
    model.AddMaxEquality(delivery_date_IntVar[a], [delivery_times[a, t] * x[(a, t)] for t in T])

travel_time = {}
deadline_not_met = {}
additional_deadline_not_met = {}
days_too_late = {}
result_division = {}
result_division2 = {}
travel_time2 = {}
result_division3 = {}
intermediate_result = {}
days_over_net_transport = {}
for a in A:
    for t in T:
        # cost_no_deadline[a] = model.NewIntVar(0, 1000, f'cost_no_deadline_{a}')
        travel_time[a, t] = model.NewIntVar(0, int(pd.Timestamp.max.timestamp()), "travel_time")
        deadline_not_met[a, t] = model.NewBoolVar('deadline_not_met')
        additional_deadline_not_met[a, t] = model.NewBoolVar('additional_deadline_not_met')
        days_too_late[a, t] = model.NewIntVar(0, int(pd.Timestamp.max.timestamp()), "days_too_late")
        result_division[a, t] = model.NewIntVar(0, int(pd.Timestamp.max.timestamp()), "result_division")
        result_division2[a, t] = model.NewIntVar(0, int(pd.Timestamp.max.timestamp()), "result_division2")
        travel_time2[a, t] = model.NewIntVar(0, int(pd.Timestamp.max.timestamp()), "travel_time2")
        # can be negative as the result can be negative, but if negative will not be used then for final
        result_division3[a, t] = model.NewIntVar(-int(pd.Timestamp.max.timestamp()), int(pd.Timestamp.max.timestamp()), "result_division3")
        intermediate_result[a, t] = model.NewIntVar(0, int(pd.Timestamp.max.timestamp()), "intermediate_result")
        days_over_net_transport[a, t] = model.NewIntVar(0, int(pd.Timestamp.max.timestamp()), "days_over_net_transport")
        

# compute the costs induced by a single car
# def compute_car_costs_modified(avlDate, dueDate, deliveryDate, referenceTime, a, x):
#     costs = 0
#     for t in T:
#         # is not 0 iff x[a, t] != 0
#         costs += x[a, t] * compute_car_costs_modified_per_car(avlDate, dueDate, deliveryDate, referenceTime, travel_time[a])
#     return costs

def compute_car_costs_modified(avlDate, dueDate, deliveryDate, referenceTime, a, x):
    costs = 0
    for t in T:
        # is not 0 iff x[a, t] != 0
        # i cannot multiply by x[a, t] because it would not be linear anymore, as the result of the function is a IntVar
        code_t, _ = t
        # only look at last transport as only this is relevant for computing costs
        if get_attribute_of_car(a, "DestinationCode") == S[code_t]["DestinationCode"]:
            costs += compute_car_costs_modified_per_car(avlDate, dueDate, deliveryDate, referenceTime, travel_time[a, t], x[a, t], deadline_not_met[a, t], days_too_late[a, t], result_division[a, t], result_division2[a, t], travel_time2[a, t], result_division3[a, t], additional_deadline_not_met[a, t], intermediate_result[a, t], days_over_net_transport[a, t])
    return costs


# compute the costs induced by a single car
def compute_car_costs_modified_per_car(avlDate, dueDate, deliveryTime, referenceTime, travel_time, x, deadline_not_met, days_too_late, result_division, result_division2, travel_time2, result_division3, additional_deadline_not_met, intermediate_result, days_over_net_transport):
    # case 1: car has no deadline -> 1 euro per day before arrival
    avlTime = int(float(avlDate.timestamp()))
    if dueDate == "-":
        model.Add(travel_time == deliveryTime - avlTime).OnlyEnforceIf(x)
        model.Add(travel_time == 0).OnlyEnforceIf(x.Not())
        #arrival_day = #TODO: implement the replace:.replace(hour=0, minute=0, second=0, microsecond=0) # only count time before arrival day, ist nur egal wenn immmer um 0 uhr ankommt
        model.AddDivisionEquality(result_division, travel_time, (60 * 60 * 24)) # cast number of seconds to number of days
        return result_division
    else:
        # case 2: car has a deadline -> componentwise costs:
        dueTime = int(float(dueDate.timestamp()))
        model.Add(deliveryTime > dueTime).OnlyEnforceIf(deadline_not_met)
        model.Add(deliveryTime <= dueTime).OnlyEnforceIf(deadline_not_met.Not())
        model.AddDivisionEquality(result_division2, (deliveryTime - dueTime), (60 * 60 * 24))
        # inequality to round up
        model.Add(days_too_late >= result_division2).OnlyEnforceIf(x)
        model.Add(days_too_late == 0).OnlyEnforceIf(x.Not())

        # travel_time2: time from availability to delivery; check if this time is too long
        double_reference_time = 2 * int(referenceTime)
        model.AddDivisionEquality(travel_time2, (deliveryTime-avlTime), (60 * 60)) 
        model.Add(travel_time2 - double_reference_time > 0).OnlyEnforceIf(additional_deadline_not_met)
        model.Add(travel_time2 - double_reference_time <= 0).OnlyEnforceIf(additional_deadline_not_met.Not())
        
        model.AddDivisionEquality(result_division3, travel_time2 - double_reference_time, (24))
        # # # inequality to round up i.e. math.ceil
        model.Add(days_over_net_transport >= result_division3).OnlyEnforceIf(additional_deadline_not_met)
        model.Add(days_over_net_transport == 0).OnlyEnforceIf(additional_deadline_not_met.Not())

        model.Add(intermediate_result == 100 * deadline_not_met + 25 * days_too_late + 5 * days_over_net_transport).OnlyEnforceIf(x)
        model.Add(intermediate_result == 0).OnlyEnforceIf(x.Not())
        
        return intermediate_result


# def custom_objective(int_var, bool_var, normal_var):
#     cost_deadline_missed = model.NewIntVar(0, 1000000, 'cost_deadline_missed')
#     # Define a custom objective function
#     cost = 0
#     condition = model.NewBoolVar('condition')
#     model.Add(int_var > normal_var).OnlyEnforceIf(condition)
#     model.Add(int_var <= normal_var).OnlyEnforceIf(condition.Not())
#     model.Add(cost == 100 * condition)
#     return cost

total_costs = sum(compute_car_costs_modified(
                dataframes_type_casted["TRO"][(dataframes_type_casted["TRO"]['ID(long)'] == a)].iloc[0]["AvailableDateOrigin"], 
                dataframes_type_casted["TRO"][(dataframes_type_casted["TRO"]['ID(long)'] == a)].iloc[0]["DueDateDestinaton"], 
                delivery_date_IntVar[a],
                cars[a]['deliveryRef'],
                a,
                x) for a in A)

print("Solving ...")
model.Minimize(total_costs)
# model.Minimize(sum(custom_objective(delivery_date_IntVar[a], 
#                                     x[a, t], 
#                                     int(a)) for a, t in zip(A, T)))

# model.ExportToFile("model_of_file_" + file_path)
solver = cp_model.CpSolver()

status = solver.Solve(model)
print("  - wall time       : %f s" % solver.WallTime())
# Check the result and print the values
if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print('Solution:')
    for a in A:
        for t in T:
            if solver.Value(x[(a, t)]) == 1:
                print(f'x[{a},{t}] = {solver.Value(x[(a, t)])}')
    print('Objective value:', solver.ObjectiveValue())
else:
    print('The problem does not have an optimal solution.')

breakpoint()