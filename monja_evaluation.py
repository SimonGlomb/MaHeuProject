import math
from datetime import timedelta


# compute the costs induced by a single car
def compute_car_costs(avlDate, dueDate, deliveryDate, referenceTime):
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

    return cost

# compute the value of the complete solution
def compute_total_costs(cars):
    costs = 0
    for car_id in cars.keys():
        costs += compute_car_costs(cars[car_id]['avlDate'], cars[car_id]['dueDate'], cars[car_id]['currentDelivery'], cars[car_id]['deliveryRef'])
    return costs

# print all relevant routing information of the given car in a nice format
def print_timetable(car, segments):
    print(f"origin: {car['origin']}, available at {car['avlDate']}")
    if car['assignedPath'] == None:
        print("no route assigned")
    else:
        for s, t in car['schedule']:
            print(f"({s}): {segments[s]['start']} -> {segments[s]['end']}, departure: {t}, arrival: {t + timedelta(hours=segments[s]['duration'])}")
    print(f"destination: {car['destination']}, due at: {car['dueDate']}, net delivery time (reference): {car['deliveryRef']/24} day(s)")
    delivery_time = (car['currentDelivery']-car['avlDate']).total_seconds()/(60*60*24)
    delay = 0
    overtime = 0
    if car['dueDate'] != "-":
        delay = (car['currentDelivery']-car['dueDate']).total_seconds()/(60*60*24)
        overtime = max(0, delivery_time - (2*car['deliveryRef']/24))
    print(f"total delivery time: {delivery_time} day(s), delay: {delay} day(s), time over 2x net delivery: {overtime} day(s)")
    print(f"=> cost: {car['inducedCosts']}")
    return

# print the routing information of all cars (maybe into a file later)
def print_all_timetables(cars, segments):
    for car in cars.keys():
        print(f"------------------------------------------------------------------------------------------------\nCar {car}\n------------------------------------------------------------------------------------------------")
        print_timetable(cars[car], segments)
    return

# compute utilization of specific transports and the respective car ids
def compute_transport_usage(cars, segments):
    used_capacity = {}
    assignments = {}
    keys = [(s,t) for s in segments.keys() for t in segments[s]['timeslots'].keys()]
    for key in keys:
        assigned_cars = [id for id in cars.keys() if key in cars[id]['schedule']] # all cars using segment s at time t
        used_capacity[key] = len(assigned_cars)
        assignments[key] = assigned_cars
    return used_capacity, assignments

# print the assignment of cars to transports
def print_transport_usage(cars, segments):
    used_capacities, assignments = compute_transport_usage(cars, segments)
    print(f"Cars {[c for c in cars.keys() if cars[c]['assignedPath'] == None]} are not delivered.")
    for s in segments.keys():
        print("-----------------------------------------")
        print(f"Segment {s}: {segments[s]['name']}")
        print("-----------------------------------------")
        for t in segments[s]['timeslots'].keys():
            free_capacity = int(segments[s]['timeslots'][t])
            used_capacity = used_capacities[(s,t)]
            print(f"{t}: {used_capacity}/{free_capacity+used_capacity} used | {assignments[(s,t)]}")
            print(".................................")

    return

# check wether the schedules of the given cars represent correct paths and respect time and capacity constraints
def validate_assignments(cars, segments):
    valid = True
    # check path properties and timing constraints
    for c in cars.keys():
        if cars[c]['assignedPath'] == None: # no path is bad, but no misstake
            continue
        if segments[cars[c]['schedule'][0][0]]['start'] != cars[c]['origin']: # start of path is not correct origin
            valid = False
            print_timetable(cars[c], segments)
            continue
        if cars[c]['schedule'][0][1] < cars[c]['avlDate']: # starttime violates available date
            valid = False
            print_timetable(cars[c], segments)
            continue
        if segments[cars[c]['schedule'][-1][0]]['end'] != cars[c]['destination']: # end of path is not correct destination
            valid = False
            print_timetable(cars[c], segments)
            continue
        for i in range(len(cars[c]['schedule'][1:])): 
            s,t = cars[c]['schedule'][i+1] # current segment
            q,r = cars[c]['schedule'][i] # previous segment
            if segments[s]['start'] != segments[q]['end']: # path is not really a path
                valid = False
                print_timetable(cars[c], segments)
                break
            if t < (r + timedelta(hours=segments[q]['duration']+24)).replace(hour=0, minute=0, second=0, microsecond=0): # path does not respect timing (transporttimes and waiting times)
                valid = False
                print_timetable(cars[c], segments)
                break
    if valid:
        print("all assingments ok")

    # check capacity constraints
    res_cap = [segments[s]['timeslots'][t] for s in segments.keys() for t in segments[s]['timeslots'].keys()] # tracked remaining capacities. should all be >= 0
    if min(res_cap) < 0:
        valid = False
        print("error in capacity tracking and/or utilization")

    # check that transport capacities are not violated
    transports = [(s,t) for s in segments.keys() for t in segments[s]['timeslots'].keys()] # all arcs
    used_caps, assigned_cars = compute_transport_usage(cars, segments)
    for s,t in transports:
        if used_caps[(s,t)] > segments[s]['capacities'][t]: # cars using segment s at time t are more than allowed
            valid = False
            print(f"capacity of segment {s} at {t} is exceeded: cap = {segments[s]['capacities'][t]}, used = {used_caps[(s,t)]}: {assigned_cars[(s,t)]}")
            continue
    if valid:
        print("all capacities are respected")
    return valid

