#imports
import pandas as pd
from datetime import datetime, timedelta
import math
import random

#################### teststuff #######################
import parse_txt
######################################################

# stolen from preprocessing.py to convert date-string into something to work with 
def handle_dates(date_str):
    if date_str == "-":
        return date_str
    else:
        return datetime.strptime(date_str, '%d/%m/%Y-%H:%M:%S')

# computes the last date of the viewed timeframe (latest arrival of a planned transport)
def end_of_timeframe(segments):
    # for each segments compute the arrivaltime for the latest timeslot -> maximum arrival time is the end of the timeframe
    arrivals = [max(segments[s]['timeslots'].keys()) + timedelta(hours=segments[s]['duration']) for s in segments.keys() if len(segments[s]['timeslots'].keys()) != 0]
    eot = max(arrivals)
    return eot

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

# find the earliest possible timeslots (and corresponding path) for a car
def assign_timeslots(car, paths, segments, eot):
    path = None
    departures = []
    earliest_arrival = None

    # for all potential paths, check the earliest arrival date -> pick the best one
    for i in range(len(car['paths'])):
        p = car['paths'][i]
        earliest_start = car['avlDate']
        current_timetable = []
        for j in range(len(paths[p])):
            potential_times = [s for s in segments[paths[p][j]]['timeslots'].keys() if s >= earliest_start and segments[paths[p][j]]['timeslots'][s] > 0] # timeslots after the ealiest possible departure with open capacities
            if len(potential_times) > 0:
                departure = min(potential_times)
            else: # path is blocked -> try the next path
                break
            current_timetable.append(departure)
            if j != len(paths[p])-1: # determine ealiest departure from current location
                earliest_start = (departure + timedelta(hours=segments[paths[p][j]]['duration']+24)).replace(hour=0, minute=0, second=0, microsecond=0)
            else: # last segment: determine arrival time
                arrival = departure + timedelta(hours=segments[paths[p][j]]['duration'])
                if earliest_arrival == None or arrival < earliest_arrival:
                    earliest_arrival = arrival
                    departures = current_timetable
                    path = p
          
    if departures == []: # all paths are blocked, pretend that car arrives at the end of timeframe but assign no path
        return [], None, eot
    
    return departures, path, earliest_arrival

# find earliest route to a destination starting from an intermediate location
def earliest_timeslots_from_loc(car, paths, segments, start_loc, start_time, eot):
    departures = []
    earliest_arrival = None
    path = None # path used to complete the route
    index = None # index of the path-segment leaving the start location

    # check arrival times for all potential paths and pick the best one
    for i in range(len(car['paths'])):
        p = car['paths'][i]
        current_timetable = []
        earliest_start = start_time
        # check if path p contains start_loc, and if so, at which position
        stops = [segments[s]['start'] for s in paths[p]]
        if start_loc in stops:
            start_index = stops.index(start_loc)
        else: # if p does not contain start_loc, skip it
            break
        
        # traverse segments (starting in start location) and pick the earliest possible timeslots
        for j in range(len(paths[p][start_index:])):
            potential_times = [s for s in segments[paths[p][start_index + j]]['timeslots'].keys() if s >= earliest_start and segments[paths[p][start_index + j]]['timeslots'][s] > 0] # timeslots after the ealiest possible departure with open capacities
            if len(potential_times) > 0:
                departure = min(potential_times)
            else: # path is blocked -> continue with next path
                break
            current_timetable.append(departure)
            if j != len(paths[p][start_index:])-1: # compute earliest allowed departure time from current location
                earliest_start = (departure + timedelta(hours=segments[paths[p][start_index + j]]['duration']+24)).replace(hour=0, minute=0, second=0, microsecond=0)
            else: # last segment: determine arrival time
                arrival = departure + timedelta(hours=segments[paths[p][start_index + j]]['duration'])
                if earliest_arrival == None or arrival < earliest_arrival: # find earliest of the potential arrival times
                    earliest_arrival = arrival
                    departures = current_timetable
                    path = p
                    index = start_index
          
    if departures == []: # if all paths are blocked, pretend that car arrives at the end of timeframe
        return departures, None, None, eot
    
    return departures, path, index, earliest_arrival

# compute a very simple lower bound on the costs induced by the given car
def simple_lower_bound(car, paths, segments, eot):
    # determine earliest possible delivery date
    earliest_arrival = assign_timeslots(car, paths, segments, eot)[2]
    return compute_car_costs(car['avlDate'], car['dueDate'], earliest_arrival, car['deliveryRef'])

# compute upper bound for the costs induced by a single car
def simple_upper_bound(car, end_timeframe):
    # costs if tha rar arrives at the last dat of the timeframe
    return compute_car_costs(car['avlDate'], car['dueDate'], end_timeframe, car['deliveryRef'])

# print all relevant routing information of the given car in a nice format
def print_timetable(car, segments):
    print(f"origin: {car['origin']}, available at {car['avlDate']}")
    if car['assignedPath'] == None:
        print("no route assigned")
    else:
        for s, t in car['schedule']:
            print(f"{segments[s]['start']} -> {segments[s]['end']}, departure: {t}, arrival: {t + timedelta(hours=segments[s]['duration'])}")
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


# transform the data from the dataframes of the file input into more intuitive structures
# only keep the relevant information and precompute some relevant values
def construct_instance(dataframes):
    cars={}
    paths={}
    segments={}

    car_df = dataframes['TRO']
    path_df = dataframes['PTH']
    pthseg_df = dataframes['PTHSG']
    segment_df = dataframes['SEG']
    departures_df = dataframes['PTR']

    # extract paths
    for i in path_df.index:
        id = path_df['ID(long)'][i]
        path = [] # corresponding path segments in the correct order
        path_segments = pthseg_df[pthseg_df['PathID(long)'] == id].sort_values('SegmentSequenceNumber')
        for j in path_segments.index:
            code = path_segments['SegmentCode'][j]
            sid = segment_df[segment_df['Code'] == code]['ID(long)'].iloc[0]
            path.append(sid)
        paths[id] = path

    # extract path-segments
    for i in segment_df.index:
        id = segment_df['ID(long)'][i]
        code = segment_df['Code'][i]
        segment = {'duration':float(segment_df['DefaultLeadTimeHours'][i]), 'start':segment_df['OriginCode'][i] , 'end':segment_df['DestinationCode'][i], 'name':code}
        timeslots = {}
        capacities = {}
        departures = departures_df[departures_df['PathSegmentCode'] == code]
        for j in departures.index:
            date_string = departures['TimeSlotDate'][j]
            key = handle_dates(date_string)
            timeslots[key] = float(departures['Capacity'][j]) # here the remaining capacity is tracked
            capacities[key] = float(departures['Capacity'][j]) # here the total capacity ist stored for reference

        segment['timeslots'] = timeslots
        segment['capacities'] = capacities
        segments[id] = segment

    # determine end of timeframe
    eot = end_of_timeframe(segments)

    # extract cars
    for i in car_df.index:
        id = car_df['ID(long)'][i]
        car = {'avlDate':handle_dates(car_df['AvailableDateOrigin'][i]), 
             'dueDate':handle_dates(car_df['DueDateDestinaton'][i])}
        
        # find possible paths for the car
        start = car_df['OriginCode'][i]
        car['origin'] = start
        end = car_df['DestinationCode'][i]
        car['destination'] = end
        filtered_paths = path_df[(path_df['PathOriginCode'] == start) & (path_df['PathDestinationCode'] == end)]
        pths=[]
        for j in filtered_paths.index:
            pths.append(filtered_paths['ID(long)'][j])
        car['paths'] = pths

        # compute the net transport time (hours)
        earliest_arrival = assign_timeslots(car, paths, segments, eot)[2]
        ref = (earliest_arrival - car['avlDate']).total_seconds()/(60*60)
        car['deliveryRef'] = ref

        # lower bound for the costs
        car['costBound'] = simple_lower_bound(car, paths, segments, eot)

        # set remaining values to empty values (they are set during the algorithm)
        car['assignedPath'] = None
        car['currentDelivery'] = None
        car['schedule'] = []
        car['inducedCosts'] = None

        cars[id] = car

    return cars, paths, segments, eot

# greedy algorithm
def greedy(cars, paths, segments, eot):
    # replace "no deadline" with deadline eot + 1d to allow sorting
    for id in cars.keys():
        if cars[id]['dueDate'] == "-":
            cars[id]['dueDate'] = eot + timedelta(hours=24)

    # greedy algorithm -> variants
    car_list = sorted([(id, cars[id]['avlDate'], cars[id]['dueDate']) for id in cars.keys()], key=lambda car: (car[2],car[1])) # sort by duedate, then age
    # car_list = sorted([(id, cars[id]['avlDate'], cars[id]['dueDate']) for id in cars.keys()], key=lambda car: (car[2]-car[1],car[2])) # sort by space (difference avl and due)
    # car_list = sorted([(id, simple_upper_bound(cars[id], paths, segments), cars[id]['dueDate']) for id in cars.keys()], key=lambda car: (car[1],car[2]), reverse=True) # sort descending by upper bound
    # car_list = sorted([(id, simple_upper_bound(cars[id], paths, segments)-simple_lower_bound(cars[id], paths, segments), cars[id]['dueDate']) for id in cars.keys()], key=lambda car: (car[1],car[2]), reverse=True) # sort descending by upper-lower bound

    # undo changes in due-date to not cause side effects
    for id in cars.keys():
        if cars[id]['dueDate'] == eot + timedelta(hours=24):
            cars[id]['dueDate'] = "-"

    # assign timeslots with earliest arrival
    for i in range(len(car_list)):
        id = car_list[i][0]
        d, p, a = assign_timeslots(cars[id], paths, segments, eot)
        # link car to chosen path, save corresponding delivery date
        cars[id]['assignedPath'] = p
        cars[id]['currentDelivery'] = a

        # construct a [(segID, time)]-shaped schedule and assign it to car
        schedule = []
        if p!= None:
            path = paths[p] # path segments the car is assigned to 
            for s in range(len(path)):
                schedule.append((path[s], d[s]))
        cars[id]['schedule'] = schedule

        # block used capacities in transport segments (if a path was assigned)
        if p != None:
            for j in range(len(d)):
                segments[paths[p][j]]['timeslots'][d[j]] -= 1
    
    return cars, segments

# subroutine for local search
# exactly as greedy, but starts with a random ordering of the cars
def random_greedy(cars, paths, segments, eot):
    nd = 0 # for analysis: count non delivered cars

    # randomly shuffle the cars
    car_list = [k for k in cars.keys()]
    random.shuffle(car_list)
    
    # assign timeslots with earliest arrival
    for i in range(len(car_list)):
        id = car_list[i]
        d, p, a = assign_timeslots(cars[id], paths, segments, eot)

        # link car to chosen path, save corresponding delivery date
        cars[id]['assignedPath'] = p
        cars[id]['currentDelivery'] = a

        # if a path was assigned, construct schedule and block capacities
        if p != None:
            # assign [(segID, time)] shaped schedule to car
            schedule = []
            path = paths[p] # path segments the car is assigned to 

            for s in range(len(path)):
                schedule.append((path[s], d[s]))
            cars[id]['schedule'] = schedule

            for j in range(len(d)):
                segments[paths[p][j]]['timeslots'][d[j]] -= 1
        else:
            cars[id]['schedule'] = []
            nd += 1        
       
    print(f"{nd} car(s) have no assigned path")
    # link to each car the costs it has in the current sulution
    for car_id in cars.keys():
        car_cost = compute_car_costs(cars[car_id]['avlDate'], cars[car_id]['dueDate'], cars[car_id]['currentDelivery'], cars[car_id]['deliveryRef'])
        cars[car_id]['inducedCosts'] = car_cost
    
    return cars, segments

# simple local search approach: try to swap the paths of two cars with the same start and end location
def local_search(cars, paths, segments, eot):
    cars, segments = random_greedy(cars, paths, segments, eot) # start with the solution of the random greedy assignment

    swaps_made = 0 # for analysis: count successful swapping operations
    swapped = True # track if a solution from the current neighborhood has been selected
 
    while swapped:
        swapped = False
        # cars which currently have a path and costs higher than their lower bound
        swap_candidates = [c for c in cars.keys() if cars[c]['inducedCosts'] > cars[c]['costBound'] and cars[c]['assignedPath'] != None]

        for i in swap_candidates:
            # cars to potentially swap with (same start- and endpoint, compatible starttimes)
            partners = [c for c in cars.keys() if cars[c]['origin'] == cars[i]['origin'] and cars[c]['destination'] == cars[i]['destination']
                        and (cars[c]['assignedPath'] == None or cars[c]['schedule'][0][1] >= cars[i]['avlDate']) and cars[i]['schedule'][0][1] >= cars[c]['avlDate']]
        
            for p in partners:
                new_costs_i = compute_car_costs(cars[i]['avlDate'], cars[i]['dueDate'], cars[p]['currentDelivery'], cars[i]['deliveryRef'])
                new_costs_p = compute_car_costs(cars[p]['avlDate'], cars[p]['dueDate'], cars[i]['currentDelivery'], cars[p]['deliveryRef'])

                # difference: current costs - costs after swap
                diff = cars[i]['inducedCosts'] + cars[p]['inducedCosts'] - (new_costs_i + new_costs_p)
                if diff > 0: # if new costs are lower, swap schedules of i and p
                    temp = (cars[i]['assignedPath'], cars[i]['schedule'], cars[i]['currentDelivery'])
                    cars[i]['assignedPath'] = cars[p]['assignedPath']
                    cars[i]['schedule'] = cars[p]['schedule']
                    cars[i]['currentDelivery'] = cars[p]['currentDelivery']
                    cars[i]['inducedCosts'] = new_costs_i

                    cars[p]['assignedPath'] = temp[0]
                    cars[p]['schedule'] = temp[1]
                    cars[p]['currentDelivery'] = temp[2]
                    cars[p]['inducedCosts'] = new_costs_p

                    swaps_made += 1
                    swapped = True
                    break
            if swapped:
                break
 
    print(f"swaps made: {swaps_made}")
    return cars, segments

# advanced local search approach: swapping only partial paths is allowed, swapping with free segments is also possible
def advanced_local_search(cars, paths, segments, eot):
    cars, segments = random_greedy(cars, paths, segments, eot) # start with the solution of the random greedy assignment

    swaps_made = 0 # for analysis: count successful swapping operations
    partials = 0 # swaps that did not swap full paths
    shifts = 0 # swaps to free paths
    partial_shifts = 0

    swapped = True # check if a solution from the neighborhood has been selected
    while swapped:
        swapped = False
        # cars with costs over lower bound
        swap_candidates = [c for c in cars.keys() if cars[c]['inducedCosts'] > cars[c]['costBound']]
        for i in swap_candidates:
            # determine from how many locations the new path can diverge from the old one
            if cars[i]['assignedPath'] == None:
                    checkpoints = 1
                    # potential partners: cars with same destination and assigned path
                    partners = [c for c in cars.keys() if cars[c]['destination'] == cars[i]['destination'] and cars[c]['assignedPath'] != None]
            else:
                path_segs_i = paths[cars[i]['assignedPath']]
                checkpoints = len(path_segs_i)
                # cars to potentially swap with (same destination)
                partners = [c for c in cars.keys() if cars[c]['destination'] == cars[i]['destination']]

            # check at which location and time replacement path has to start
            for x in range(checkpoints):
                if x == 0:
                    earliest_start_i = cars[i]['avlDate']
                    start_location = cars[i]['origin']
                else:
                    # arrival of the x-1-th transport + waiting time
                    earliest_start_i = (cars[i]['schedule'][x-1][1] + timedelta(hours=24+segments[path_segs_i[x-1]]['duration'])).replace(hour=0, minute=0, second=0, microsecond=0)
                    start_location = segments[path_segs_i[x]]['start']

                for p in partners:
                    # filter partners: their path has to contain the start location, the starting timeslots must be compatible
                    if cars[p]['assignedPath'] == None and cars[p]['origin'] == start_location: # cars without a path can only be part of a complete swap (from position 0)
                        if x == 0:
                            index = 0
                            earliest_start_p = cars[p]['avlDate']
                        else:
                            continue
                    elif cars[p]['assignedPath'] != None: # for cars with path: determine crossing position and departure
                        path_segs_p = paths[cars[p]['assignedPath']]
                        stops = [segments[s]['start'] for s in paths[cars[p]['assignedPath']]]
                        if start_location in stops:
                            index = stops.index(start_location)
                            if index == 0:
                                earliest_start_p = cars[p]['avlDate']
                            else:
                                # arrival of the x-1-th transport + waiting time
                                earliest_start_p = (cars[p]['schedule'][index-1][1] + timedelta(hours=24+segments[path_segs_p[index-1]]['duration'])).replace(hour=0, minute=0, second=0, microsecond=0)
                        else: # if i and p dont cross in the desired location, skip p
                            continue
                    else: # cars without a path and a different origin than i are skipped
                        continue
                    # check if starttimes at the crossing-location can be swapped without violationg time constraints
                    if (cars[i]['assignedPath'] == None or cars[i]['schedule'][x][1] >= earliest_start_p) and (cars[p]['assignedPath'] == None or cars[p]['schedule'][index][1] >= earliest_start_i):
                        # compute costs after the swap
                        new_costs_i = compute_car_costs(cars[i]['avlDate'], cars[i]['dueDate'], cars[p]['currentDelivery'], cars[i]['deliveryRef'])
                        new_costs_p = compute_car_costs(cars[p]['avlDate'], cars[p]['dueDate'], cars[i]['currentDelivery'], cars[p]['deliveryRef'])

                        # difference: current costs - costs after swap
                        diff = cars[i]['inducedCosts'] + cars[p]['inducedCosts'] - (new_costs_i + new_costs_p)

                        if diff > 0: # if new costs are lower, swap the chosen parts of p and i
                            temp = (cars[i]['schedule'], cars[i]['currentDelivery'])
                            cars[i]['schedule'] = cars[i]['schedule'][:x] + cars[p]['schedule'][index:]
                            cars[i]['currentDelivery'] = cars[p]['currentDelivery']
                            cars[i]['inducedCosts'] = new_costs_i
                            # find path id of the new path
                            path_i = [path_index for path_index, path_segments in paths.items() if path_segments == [s for s,t in cars[i]['schedule']]]
                            if len(path_i) > 0:
                                cars[i]['assignedPath'] = path_i[0]
                            else:
                                cars[i]['assignedPath'] = None

                            cars[p]['schedule'] = cars[p]['schedule'][:index] + temp[0][x:]
                            cars[p]['currentDelivery'] = temp[1]
                            cars[p]['inducedCosts'] = new_costs_p
                            # find path id of the new path
                            path_p = [path_index for path_index, path_segments in paths.items() if path_segments == [s for s,t in cars[p]['schedule']]]
                            if len(path_p) > 0:
                                cars[p]['assignedPath'] = path_p[0]
                            else:
                                cars[p]['assignedPath'] = None

                            swaps_made += 1
                            if x > 0:
                                partials += 1

                            swapped = True
                            break
                if swapped: 
                    break
            if swapped:
                break
            else: # try using free capacities to replace the last x+1 segments of the path            
                # free capacities of the last x+1 segments currently used:
                for s,t in cars[i]['schedule'][checkpoints-(x+1):]:
                    segments[s]['timeslots'][t] += 1

                if x == checkpoints-1: # if we swap the whole path..
                    earliest_start_i = cars[i]['avlDate']
                    start_location = cars[i]['origin']
                else: # determine start location and earliest start time of replacement path
                    # arrival of the (x+2)nd-last transport + waiting time
                    earliest_start_i = (cars[i]['schedule'][checkpoints-(x+2)][1] + timedelta(hours=24+segments[path_segs_i[checkpoints-(x+2)]]['duration'])).replace(hour=0, minute=0, second=0, microsecond=0)
                    start_location = segments[path_segs_i[checkpoints-(x+1)]]['start']

                # determine replacement path with earliest arrival
                departures, path, index, arrival = earliest_timeslots_from_loc(cars[i], paths, segments, start_location, earliest_start_i, eot)
                if arrival < cars[i]['currentDelivery']: # swap if new path arrives earlier
                    # update schedule
                    schedule = []
                    path_segments = paths[path][index:] # new path segments

                    # construct schedule for new path segments and replace the old ones
                    for seg in range(len(path_segments)): 
                        schedule.append((path_segments[seg], departures[seg]))
                    cars[i]['schedule'] = cars[i]['schedule'][:checkpoints-(x+1)] + schedule

                    # link car to chosen path, save corresponding delivery date
                    cars[i]['currentDelivery'] = arrival
                    path_i = [path_index for path_index, path_segments in paths.items() if path_segments == [s for s,t in cars[i]['schedule']]][0]
                    cars[i]['assignedPath'] = path_i

                    shifts += 1
                    swaps_made += 1
                    if x+1 < checkpoints:
                        partial_shifts += 1

                    cars[i]['inducedCosts'] = compute_car_costs(cars[i]['avlDate'], cars[i]['dueDate'], cars[i]['currentDelivery'], cars[i]['deliveryRef'])
                    swapped = True

                # block/restore used capacities:
                for s,t in cars[i]['schedule'][checkpoints-(x+1):]:
                    segments[s]['timeslots'][t] -= 1
                if swapped:
                    break

    print(f"swaps made: {swaps_made}, partials: {partials}, shifts: {shifts}, partial shifts: {partial_shifts}")
    return cars, segments


###################### do stuff #######################
import sys
import monja_utility
from monja_evaluation import print_all_timetables
from monja_algorithms.greedy import greedy
instances = ["1","2a","2b","2c","3","4","5a","5b","6a","6b","6c","6d","6e","6f","6g",]

for i in range(len(instances)):
    df=parse_txt.parse_file(f"data\inst00{instances[i]}.txt")
    a,b,c,d = construct_instance(df)
    print(instances[i])
    res = local_search(a,b,c,d)
    print(compute_total_costs(res[0]))
    lbs = [res[0][i]['costBound'] for i in res[0].keys()]
    print(f"lb: {sum(lbs)}")
    validate_assignments(res[0], res[1])
    print("--------------------")

# original_stdout = sys.stdout 
# with open('results\demo.txt', 'w') as f:
#     sys.stdout = f
#     print_all_timetables(res[0], res[1])
#     # Reset the standard output
#     sys.stdout = original_stdout

