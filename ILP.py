import parse_txt
import datetime
import pandas as pd
import math

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
# path_origin to look if it can be used by a car, i.e. if the segment is useable for reaching the final destination
S = {(code, origin, destination, pathcode, path_origin, path_destination) for code, origin, destination, pathcode, path_origin, path_destination in zip(dataframes_type_casted["PTHSG"]["SegmentCode"].iloc[0], 
                                                                      dataframes_type_casted["PTHSG"]["SegmentOriginCode"].iloc[0],
                                                                      dataframes_type_casted["PTHSG"]["SegmentDestinationCode"].iloc[0],
                                                                      dataframes_type_casted["PTHSG"]["PathCode"].iloc[0],
                                                                      dataframes_type_casted["PTH"][(dataframes_type_casted["PTH"]["PathCode"] == dataframes_type_casted["PTHSG"]["PathCode"].iloc[0])].iloc[0]["PathOriginCode"], # TODO: gucken ob ich iloc[0] machen darf
                                                                      dataframes_type_casted["PTH"][(dataframes_type_casted["PTH"]["PathCode"] == dataframes_type_casted["PTHSG"]["PathCode"].iloc[0])].iloc[0]["PathDestinationCode"], # TODO: gucken ob ich iloc[0] machen darf
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



# DEFINE CONSTANTS
# has due date
d = {}
for a in A:
    if dataframes_type_casted["TRO"][(dataframes_type_casted["TRO"]['ID(long)'] == a)].iloc[0]["DueDateDestinaton"] == "-":
        d[a] = 0
    else:
        d[a] = 1

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

# ensure that we wait at a place leadtimehours + 24 hours before assigning another transport
for a in A:
    for t1 in T:
        code1, time1 = t1
        LTH = int(float(find_first_match(dataframes_type_casted["PTR"], code1, time1)["LeadTimeHours"]))
        for t2 in T:
            code2, time2 = t2
            if time2 <= time1 + pd.Timedelta(hours=LTH) + pd.Timedelta(hours=24):
                model.Add(x[(a, t1)] + x[(a, t2)] <= 1)

# ensure that every car is exactly at one position in time
# TODO: check if it is already done by the previous constraint, and with the constraint "check coherence and if this is also useful to reach final destination, i.e. using a correct path"

# ensure that car stays at origin until available date is reached
for a in A:
    for t in T:
        code, time = t
        if time < get_attribute_of_car(a, "AvailableDateOrigin"):
            model.Add(x[(a, t)] == 0)


# set constraint that we do not use transports which dont reach goals
for a in A:
    for t in T:
        for s in S:
            code_t, time = t
            code_s, origin, destination, pathcode, path_origin, path_destination = s
            if not code_t == code_s:
                model.Add(x[(a, t)] == 0)

# check coherence and if this is also useful to reach final destination, i.e. using a correct path
for a in A:
        # transport is useful for that car

        # ensure that we leave the origin
        model.Add(sum(x[(a, t)] for (code_s, origin, _, pathcode, _, _), (code_t, time_t) in zip(S, T) if code_t == code_s and get_attribute_of_car(a, "OriginCode") == origin and get_attribute_of_car(a, "DesignatedPathCode") == pathcode) == 1)

        # ensure that we reach the destination of the car
        model.Add(sum(x[(a, t)] for (code_s, _, destination, pathcode, _, _), (code_t, time_t) in zip(S, T) if code_t == code_s and get_attribute_of_car(a, "DestinationCode") == destination and get_attribute_of_car(a, "DesignatedPathCode") == pathcode) == 1)

        # Ensure no gaps and the continuity of the path; together with the ensurance that car leaves origin, it finds full path
        # now we can assume that we leave the origin, so we now have to ensure we dont stop somewhere (if it is not the destination)
        model.Add(sum(x[(a, (next_code_t, next_time_t))] for (code_t, time_t), (next_code_t, next_time_t), (code_s, origin, destination, pathcode, _, _), (next_code_s, next_origin, next_destination, next_pathcode, _, _) in zip(T, T, S, S) if code_t == code_s and next_code_t == next_code_s and destination == next_origin and next_pathcode == pathcode and origin != destination and get_attribute_of_car(a, "DesignatedPathCode") == pathcode) == 1)

        # transport path is not useful for whole goal of car a reaching its final destination
        for (_, _, _, pathcode, _, _), t in zip(S, T):
            if get_attribute_of_car(a, "DesignatedPathCode") != pathcode:
                model.Add(x[(a, t)] == 0)




# MINIMIZATION OBJECTIVE

cars, paths, segments, eot = preprocessing.construct_instance(dataframes)

delivery_dates = {}
for a in A:
    departures, assigned_path, current_delivery = utility.assign_timeslots(cars[a], paths, segments, eot)
    #
    for t in T:
        code_t, time_t = t
        LTH = int(float(find_first_match(dataframes_type_casted["PTR"], code1, time1)["LeadTimeHours"]))

        delivery_date = time_t + pd.Timedelta(hours=LTH)
        delivery_dates[a, t] = delivery_date

# def custom_objective(int_var, bool_var):
#     # Define a custom objective function
#     return bool_var * (2 * int_var + 3) + (1 - bool_var) * (1)  # Example of a custom objective function

# compute the costs induced by a single car
def compute_car_costs_modified(avlDate, dueDate, deliveryDate, referenceTime, a, x):
    # is not 0 iff x[a, t] != 0
    def costs_for_t(avlDate, dueDate, deliveryDate, referenceTime, a, x):
            # case 1: car has no deadline -> 1 euro per day before arrival
        if dueDate == "-":
            arrival_day = deliveryDate.replace(hour=0, minute=0, second=0, microsecond=0) # only count time before arrival day
            return math.ceil((arrival_day - avlDate).total_seconds()/(24*60*60)) # round UP to full days
        
        # case 2: car has a deadline -> componentwise costs:
        cost = 0
        if deliveryDate > dueDate:
            cost = cost + 100 # single time delay penalty: 100 euro
            cost = cost + 25*(math.ceil((deliveryDate-dueDate).total_seconds()/(24*60*60))) # delay penalty per day: 25 euro
        if (deliveryDate-avlDate).total_seconds()/(60*60) > 2*referenceTime:
            cost = cost + 5*(math.ceil(((deliveryDate - avlDate).total_seconds()/(60*60) - 2*referenceTime)/24)) # additional delay penalty per day (after 2*net transport time is exceeded): 5 euro
        return costs
    costs = 0
    for t in T:
        costs += x[a, t] * costs_for_t(avlDate, dueDate, deliveryDate, referenceTime, a, x)
    return costs

solver = cp_model.CpSolver()
model.Minimize(sum(compute_car_costs_modified(
                dataframes_type_casted["TRO"][(dataframes_type_casted["TRO"]['ID(long)'] == a)].iloc[0]["AvailableDateOrigin"], 
                dataframes_type_casted["TRO"][(dataframes_type_casted["TRO"]['ID(long)'] == a)].iloc[0]["DueDateDestinaton"], 
                delivery_dates[a, t],
                cars[a]['deliveryRef'],
                a,
                x) for a in A))
# model.Minimize(sum(custom_objective(delivery_times[(a)], x[a, t]) for a, t in zip(A, T)))


status = solver.Solve(model)

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