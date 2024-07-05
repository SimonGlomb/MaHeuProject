from datetime import timedelta
import random
import math


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

# subroutine for local search
# exactly as greedy, but starts with a random ordering of the cars
def random_greedy(cars, paths, segments, eot):
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
        breakpoint()

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

    # link to each car the costs it has in the current sulution
    for car_id in cars.keys():
        car_cost = compute_car_costs(cars[car_id]['avlDate'], cars[car_id]['dueDate'], cars[car_id]['currentDelivery'], cars[car_id]['deliveryRef'])
        cars[car_id]['inducedCosts'] = car_cost
    
    return cars, segments

# assign a random, valid schedule to a car
def assign_random_timeslots(car, paths, segments, eot):
    # pick a random path
    path = random.choice(car['paths'])
    earliest_start = car['avlDate']
    timetable = []
    for j in range(len(paths[path])):
        potential_times = [s for s in segments[paths[path][j]]['timeslots'].keys() if s >= earliest_start and segments[paths[path][j]]['timeslots'][s] > 0] # timeslots after the ealiest possible departure with open capacities
        if len(potential_times) > 0:
            departure = random.choice(potential_times)
        else: # path is blocked -> bad luck :(
            break
        timetable.append(departure)
        if j != len(paths[path])-1: # determine ealiest departure from current location
            earliest_start = (departure + timedelta(hours=segments[paths[path][j]]['duration']+24)).replace(hour=0, minute=0, second=0, microsecond=0)
        else: # last segment: determine arrival time
            arrival = departure + timedelta(hours=segments[paths[path][j]]['duration'])
          
    if len(timetable) < len(paths[path]): # path was blocked, assign no path
        return [], None, eot
    
    return timetable, path, arrival

# random start solution, less dense than greedy
def random_solution(cars, paths, segments, eot):
    # randomly shuffle the cars
    car_list = [k for k in cars.keys()]
    random.shuffle(car_list)
    for i in range(len(car_list)):
            id = car_list[i]
            d, p, a = assign_random_timeslots(cars[id], paths, segments, eot)

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

    # link to each car the costs it has in the current sulution
    for car_id in cars.keys():
        car_cost = compute_car_costs(cars[car_id]['avlDate'], cars[car_id]['dueDate'], cars[car_id]['currentDelivery'], cars[car_id]['deliveryRef'])
        cars[car_id]['inducedCosts'] = car_cost
        
    return cars, segments