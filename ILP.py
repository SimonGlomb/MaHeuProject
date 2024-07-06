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

dataframes = parse_txt.parse_file("./data/" + "inst001.txt")
dataframes_type_casted = parse_txt.parse_file("./data/" + "inst001.txt")
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

#TODO MACHEN DAS ES AUF LISTEN ARBEITET, wahrscheinlich viele == durch "in" ersetzen, maybe use itertools.product
# path_origin to look if it can be used by a car, i.e. if the segment is usable for reaching the final destination
S = {code: {"OriginCode": origin, "DestinationCode": destination, "PathCode": pathcode, "PathOriginCode": path_origin_code, "PathDestinationCode": path_destination_code} for code, origin, destination, pathcode, path_origin_code, path_destination_code in zip(
                                                                    dataframes_type_casted["PTHSG"]["SegmentCode"],
                                                                    dataframes_type_casted["PTHSG"]["SegmentOriginCode"],
                                                                    dataframes_type_casted["PTHSG"]["SegmentDestinationCode"],
                                                                    dataframes_type_casted["PTHSG"]["PathCode"],
                                                                    pd.Series([dataframes_type_casted["PTH"].iloc[0]["PathOriginCode"]] * ((dataframes_type_casted["PTHSG"]["PathCode"] == dataframes_type_casted["PTH"].iloc[0]["PathCode"]).sum())),
                                                                    pd.Series([dataframes_type_casted["PTH"].iloc[0]["PathDestinationCode"]] * ((dataframes_type_casted["PTHSG"]["PathCode"] == dataframes_type_casted["PTH"].iloc[0]["PathCode"]).sum())),
                                                                    )}


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

# ensure that every car is exactly at one position in time
# TODO: check if it is already done by the previous constraint, and with the constraint "check coherence and if this is also useful to reach final destination, i.e. using a correct path"

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
                      and get_attribute_of_car(a, "DesignatedPathCode") == S[code_t]["PathCode"]) # is the transport leading of our goal?
                      == 1) # we have to have exactly one of them

        # ensure that we reach the destination of the car
        model.Add(sum(x[(a, (code_t, time_t))] for (code_t, time_t) in T 
                      if get_attribute_of_car(a, "DestinationCode") == S[code_t]["DestinationCode"] 
                      and get_attribute_of_car(a, "DesignatedPathCode") == S[code_t]["PathCode"]) 
                      == 1)

        # Ensure no gaps and the continuity of the path; together with the ensurance that car leaves origin, it finds full path
        # now we can assume that we leave the origin, so we now have to ensure we dont stop somewhere
        for (code_t, time_t) in T:
            if S[code_t]["DestinationCode"] != get_attribute_of_car(a, "DestinationCode"):
                model.Add(sum(x[(a, (next_code_t, next_time_t))] for (next_code_t, next_time_t) in T# car is not at its goal yet 
                        if S[code_t]["DestinationCode"] == S[next_code_t]["OriginCode"]  # it really is a next possible transport
                        and get_attribute_of_car(a, "DesignatedPathCode") == S[code_t]["PathCode"] # transport leads on to right destination 
                ) == 1).OnlyEnforceIf(x[(a, (code_t, time_t))]) # then we have to take one of the possible transports

        # transport path is not useful for whole goal of car a reaching its final destination
        for (code_t, time_t) in T:
            # "!=" zu "in" ändern
            if get_attribute_of_car(a, "DestinationCode") != S[code_t]["PathDestinationCode"]:
                model.Add(x[(a, t)] == 0)

# ensure that we wait at a place leadtimehours for the next day before assigning another transport
# Gedanke von monja: zeitintervalle deifnieren, und es darf maximal 1 sein für alle ; man hat für jede auto-transport instanz das 
# müssen nur passen wenn beide x[a,t] == 1 ist
for a in A:
    for t1 in T:
        code1, time1 = t1
        LTH = int(float(find_first_match(dataframes_type_casted["PTR"], code1, time1)["LeadTimeHours"]))
        for t2 in T:
            code2, time2 = t2
            if time2 <= (time1 + pd.Timedelta(hours=LTH+24)).replace(hour=0, minute=0, second=0, microsecond=0):
                #prüfen das die auch nebeneinander sind, und gucken ob auf richtigem pfad
                if S[code1]["DestinationCode"] == S[code2]["OriginCode"]:# and get_attribute_of_car(a, "DestinationCode") == S[code1]["PathDestinationCode"]:
                    model.Add(x[(a, t1)] + x[(a, t2)] <= 1).OnlyEnforceIf(x[(a, (code1, time1))])


# MINIMIZATION OBJECTIVE

cars, paths, segments, eot = preprocessing.construct_instance(dataframes)

#delivery_times = {}
delivery_date_IntVar = {}
for a in A:
    #delivery_times[a] = model.NewIntVar(0, 1000000000, f'delivery_time_{a}')  # Example range in minutes
    delivery_date_IntVar[a] = model.NewIntVar(0, int(pd.Timestamp.max.timestamp()), 'max_timestamp')

delivery_times = {}
max_time_temp = {}
for a in A:
    departures, assigned_path, current_delivery = utility.assign_timeslots(cars[a], paths, segments, eot)

    for t in T:
        curr_delivery_dates = {}
        curr_max = {}
        code_t, time_t = t
        LTH = int(float(find_first_match(dataframes_type_casted["PTR"], code_t, time_t)["LeadTimeHours"]))

        delivery_date = time_t + pd.Timedelta(hours=LTH)
        delivery_times[a, t] = int(float(delivery_date.timestamp()))
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
is_greater_than_0 = {}
x_is_1_or_not_deadline = {}
x_is_1_or_not_add_deadline = {}
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
        # can be negative as the result can be negative, but will not be used then for final
        result_division3[a, t] = model.NewIntVar(-int(pd.Timestamp.max.timestamp()), int(pd.Timestamp.max.timestamp()), "result_division3")
        intermediate_result[a, t] = model.NewIntVar(0, int(pd.Timestamp.max.timestamp()), "intermediate_result")
        days_over_net_transport[a, t] = model.NewIntVar(0, int(pd.Timestamp.max.timestamp()), "days_over_net_transport")
        is_greater_than_0[a, t] = model.NewBoolVar("is_greater_than_0")
        

# compute the costs induced by a single car
# def compute_car_costs_modified(avlDate, dueDate, deliveryDate, referenceTime, a, x):
#     costs = 0
#     for t in T:
#         # is not 0 iff x[a, t] != 0
#         costs += x[a, t] * compute_car_costs_modified_per_car(avlDate, dueDate, deliveryDate, referenceTime, travel_time[a])
#     return costs

def compute_car_costs_modified(avlDate, dueDate, deliveryDate, referenceTime, a, t, x):
    costs = 0
    for t in T:
        # is not 0 iff x[a, t] != 0
        # i cannot multiply by x[a, t] because it would not be linear anymore, as the result of the function is a IntVar
        costs += compute_car_costs_modified_per_car(avlDate, dueDate, deliveryDate, referenceTime, travel_time[a, t], x[a, t], deadline_not_met[a, t], days_too_late[a, t], result_division[a, t], result_division2[a, t], travel_time2[a, t], result_division3[a, t], additional_deadline_not_met[a, t], intermediate_result[a, t], days_over_net_transport[a, t], is_greater_than_0[a, t])
    return costs
solver = cp_model.CpSolver()


# compute the costs induced by a single car
def compute_car_costs_modified_per_car(avlDate, dueDate, deliveryTime, referenceTime, travel_time, x, deadline_not_met, days_too_late, result_division, result_division2, travel_time2, result_division3, additional_deadline_not_met, intermediate_result, days_over_net_transport, is_greater_than_0):
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
        model.AddDivisionEquality(result_division2, deliveryTime - dueTime, (60 * 60 * 24))
        # inequality to round up
        model.Add(days_too_late == result_division2)

        # travel_time2: time from availability to delivery; check if this time is too long
        double_reference_time = 2 * int(referenceTime)
        model.AddDivisionEquality(travel_time2, (deliveryTime-avlTime), (60 * 60)) 
        model.Add(travel_time2 - double_reference_time > 0).OnlyEnforceIf(additional_deadline_not_met)
        model.Add(travel_time2 - double_reference_time <= 0).OnlyEnforceIf(additional_deadline_not_met.Not())
        
        model.AddDivisionEquality(result_division3, travel_time2 - double_reference_time, (24))
        # # # inequality to round up i.e. math.ceil
        model.Add(days_over_net_transport == result_division3).OnlyEnforceIf(additional_deadline_not_met)
        model.Add(days_over_net_transport == 0).OnlyEnforceIf(additional_deadline_not_met.Not())
        model.Add(days_over_net_transport == 0).OnlyEnforceIf(x.Not())

        return 100 * deadline_not_met + 25 * days_too_late + 5 * days_over_net_transport#inner_costs


## TODO: Idee, verspätung (deliveryDate-dueDate) in tagen
# dueDate + verspätung >= arrival date

def custom_objective(int_var, bool_var, normal_var):
    cost_deadline_missed = model.NewIntVar(0, 1000000, 'cost_deadline_missed')
    # Define a custom objective function
    cost = 0
    condition = model.NewBoolVar('condition')
    model.Add(int_var > normal_var).OnlyEnforceIf(condition)
    model.Add(int_var <= normal_var).OnlyEnforceIf(condition.Not())
    model.Add(cost == 100 * condition)
    return cost
    # if normal_var >10:
    #     arrival_day = (int_var // (24 * 60 * 60)) * (24 * 60 * 60)
    # return math.ceil((arrival_day - int_var).total_seconds()/(24*60*60))

    # is_late = model.NewBoolVar(f'is_late_{a}')
    # model.Add(int_var > normal_var).OnlyEnforceIf(is_late)
    # model.Add(int_var <= normal_var).OnlyEnforceIf(is_late.Not())
    # late_days = (max_timestamp[a] - normal_var)
    # model.Add(cost_deadline_missed == 100 + 25 * late_days).OnlyEnforceIf(is_late)
# if int_var > normal_var:
        # res += normal_var + int_var
    # res += cost_no_deadline
    # res += bool_var * (2 + 3) + 5 * int_var + (1 - bool_var) * (1)
    return cost_deadline_missed  # Example of a custom objective function


print("Solving ...")
model.Minimize(sum(compute_car_costs_modified(
                dataframes_type_casted["TRO"][(dataframes_type_casted["TRO"]['ID(long)'] == a)].iloc[0]["AvailableDateOrigin"], 
                dataframes_type_casted["TRO"][(dataframes_type_casted["TRO"]['ID(long)'] == a)].iloc[0]["DueDateDestinaton"], 
                delivery_date_IntVar[a],
                cars[a]['deliveryRef'],
                a,
                t,
                x) for a in A))
# model.Minimize(sum(custom_objective(delivery_date_IntVar[a], 
#                                     x[a, t], 
#                                     int(a)) for a, t in zip(A, T)))

status = solver.Solve(model)
print("  - wall time       : %f s" % solver.WallTime())
breakpoint()
# Check the result and print the values
if status == cp_model.OPTIMAL:# or status == cp_model.FEASIBLE:
    print('Solution:')
    for a in A:
        for t in T:
            if solver.Value(x[(a, t)]) == 1:
                print(f'x[{a},{t}] = {solver.Value(x[(a, t)])}')
    print('Objective value:', solver.ObjectiveValue())
else:
    print('The problem does not have an optimal solution.')