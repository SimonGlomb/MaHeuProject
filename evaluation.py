from datetime import timedelta
from preprocessing import get_all_dates
from utility import compute_car_costs
import math
import matplotlib.pyplot as plt

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

# check whether the schedules of the given cars represent correct paths and respect time and capacity constraints
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

# for a given solution (set of cars) check: which are late, on time, not delivered, structurally impossible to deliver on time or at all (and whether they have due dates)
def classify_arrivals(cars):
    cars_with_dl = [id for id in cars.keys() if cars[id]['dueDate'] != "-"]
    late_cars = [id for id in cars_with_dl if cars[id]['currentDelivery'] > cars[id]['dueDate']]
    not_delivered_cars = [id for id in cars.keys() if cars[id]['assignedPath'] == None]
    late_nd = [id for id in late_cars if cars[id]['assignedPath'] == None]
    always_late = [id for id in cars_with_dl if cars[id]['costBound'] >= 125] # not really true
    total = len(cars.keys())
    print(f"Of {len(cars_with_dl)} cars with a due date {len(late_cars)} are late. For {len(always_late)} of the cars punctual delivery is impossible.")
    print(f"In total {len(not_delivered_cars)} of the {total} cars are not delivered. {len(late_nd)} of which have due dates.")
    not_penalty_free = [id for id in cars_with_dl if cars[id]['costBound'] > 0]
    print(f"{len(not_penalty_free)} due cars are impossible to deliver cost free")
    return cars_with_dl, late_cars, not_delivered_cars, late_nd, always_late

# compute for how long a car has (unnecessarily) waited between transport segments
# in addition: how many cars are waiting at a given time and position?
def waiting_times(cars, paths, segments):
    times = get_all_dates(cars, segments)
    locations = []
    for s in segments.keys():
        if segments[s]['start'] not in locations:
            locations.append(segments[s]['start'])
        if segments[s]['end'] not in locations:
            locations.append(segments[s]['end'])

    loc_usage = {}
    for l in locations:
        loc_usage[l] = {}
        for t in times:
            loc_usage[l][t] = []

    cars_waittimes = {}
    for c in cars.keys():
        cars_waittimes[c] = {}
        if cars[c]['assignedPath'] == None: # cars that are not delivered wait in their origin until eot
            cars_waittimes[c][cars[c]['origin']] = (times[-1] - cars[c]['avlDate']).total_seconds()/(24*60*60)
            avl_index = times.index(cars[c]['avlDate'])
            for t in times[avl_index:]:
                loc_usage[cars[c]['origin']][t].append(c)
        else:
            path_locations = [segments[s]['start'] for s in paths[cars[c]['assignedPath']]] # end location is omitted, because cars "disappear" from destinations
            prev_avl = cars[c]['avlDate'] # track the earliest possible departure from current location
            prev_avl_index = times.index(prev_avl)
            for l in range(len(path_locations)):
                cars_waittimes[c][path_locations[l]] = (cars[c]['schedule'][l][1] - prev_avl).total_seconds()/(24*60*60)
                for t in times[prev_avl_index : int(cars_waittimes[c][path_locations[l]] + prev_avl_index)]:
                    loc_usage[path_locations[l]][t].append(c)
                prev_avl = (cars[c]['schedule'][l][1] + timedelta(hours=segments[cars[c]['schedule'][l][0]]['duration']+24)).replace(hour=0, minute=0, second=0, microsecond=0) # forced waiting does not count
                prev_avl_index = times.index(prev_avl)



    return times, cars_waittimes, loc_usage


# plots the number of cars waiting at each location and time
def plot_storage_use(usage, times, title):
    # usage: mapping from locations to times and carlists -> transform
    locations = usage.keys()
    for l in locations: # draw one graph for each location
        car_counts = [len(usage[l][t]) for t in times]
        plt.step(times, car_counts, where='post', label=l)
        plt.tight_layout()
    plt.legend(title='location:')
    plt.xticks(rotation=-20, ha='left')  
    plt.savefig(f'{title}.png')
    plt.close()
    return

# plot which timeslots are used how much for each segment
def plot_capacity_usage():
    return











######################################################################################
import pickle
import parse_txt
from preprocessing import construct_instance, always_late

instances = ["1","2a","2b","2c","3","4","5a","5b","6a","6b","6c","6d","6e","6f","6g",]
for i in range(len(instances)):
    df=parse_txt.parse_file(f"data\inst00{instances[i]}.txt")
    a,b,c,d = construct_instance(df)
    mapping = pickle.load(open(f"results\mapping_greedy_00{instances[i]}.txt", 'rb'))
    ts, wc, lu = waiting_times(mapping[0], b, c)
    
    plot_storage_use(lu, ts, f"usage_greedy_{instances[i]}")


