#imports
import pandas as pd
from datetime import datetime, timedelta
import math
import random

#################### teststuff #######################
import parse_txt

df=parse_txt.parse_file("data\inst003.txt")

######################################################

# stolen from preprocessing.py to convert date-string into something to work with 
def handle_dates(date_str):
    if date_str == "-":
        return date_str
    else:
        return datetime.strptime(date_str, '%d/%m/%Y-%H:%M:%S')

# computes the last date of the viewed timeframe (latest arrival of a planned transport)
def end_of_timeframe(segments):
    arrivals = [max(segments[s]['timeslots'].keys()) + timedelta(hours=segments[s]['duration']) for s in segments.keys() if len(segments[s]['timeslots'].keys()) != 0]
    eot = max(arrivals)
    return eot

# compute the costs induced by a single car
def compute_car_costs(avlDate, dueDate, deliveryDate, referenceTime):
    # case 1: car has no deadline -> 1 euro per day before arrival
    if dueDate == "-":
        arrival_day = deliveryDate.replace(hour=0, minute=0, second=0, microsecond=0) # only count time before arrival day
        # print(car['avlDate'], arrival_day, math.ceil((arrival_day - car['avlDate']).total_seconds()/(24*60*60)))
        return math.ceil((arrival_day - avlDate).total_seconds()/(24*60*60))
    
    # case 2: car has a deadline -> componentwise costs:
    cost = 0
    if deliveryDate > dueDate:
        cost = cost + 100 # single time delay penalty: 100 euro
        cost = cost + 25*(math.ceil((deliveryDate-dueDate).total_seconds()/(24*60*60))) # delay penalty per day: 25 euro
    if (deliveryDate-avlDate).total_seconds()/(60*60) > 2*referenceTime:
        cost = cost + 5*(math.ceil(((deliveryDate - avlDate).total_seconds()/(60*60) - 2*referenceTime)/24)) # additional delay penalty per day (after 2*net transport time is exceeded): 5 euro

    return cost

# compute the value of the complete solution, maybe add computation of delivery date
def compute_total_costs(cars):
    costs = 0
    for car_id in cars.keys():
        costs += compute_car_costs(cars[car_id]['avlDate'], cars[car_id]['dueDate'], cars[car_id]['currentDelivery'], cars[car_id]['deliveryRef'])
    return costs

# find the earliest possible timeslots (and corresponding path) for a car
def assign_timeslots(car, paths, segments):
    eot = end_of_timeframe(segments)
    path = car['paths'][0]
    departures = []
    earliest_arrival = None
    for i in range(len(car['paths'])):
        p = car['paths'][i]
        earliest_start = car['avlDate']
        current_timetable = []
        for j in range(len(paths[p])):
            potential_times = [s for s in segments[paths[p][j]]['timeslots'].keys() if s >= earliest_start and segments[paths[p][j]]['timeslots'][s] > 0] # timeslots after the ealiest possible departure with open capacities
            if len(potential_times) > 0:
                departure = min(potential_times)
            else: # path is blocked
                break
            current_timetable.append(departure)
            if j != len(paths[p])-1:
                earliest_start = (departure + timedelta(hours=segments[paths[p][j]]['duration']+24)).replace(hour=0, minute=0, second=0, microsecond=0)
            else: # last segment; determine arrival time
                arrival = departure + timedelta(hours=segments[paths[p][j]]['duration'])
                if earliest_arrival == None or arrival < earliest_arrival:
                    earliest_arrival = arrival
                    departures = current_timetable
                    path = p
          
    if departures == []: # all paths are blocked, pretend that car arrives at the end of timeframe
        print("blocked")
        return [], None, eot
   # print(f"path: {paths[path]}, times: {departures}, arrival: {earliest_arrival}, deadline: {car['dueDate']}")
    return departures, path, earliest_arrival

# compute a very simple lower bound on the costs induced by the given car
def simple_lower_bound(car, paths, segments):
    # determine earliest possible delivery date
    earliest_arrival = assign_timeslots(car, paths, segments)[2]
    return compute_car_costs(car['avlDate'], car['dueDate'], earliest_arrival, car['deliveryRef'])

# compute upper bound for the costs induced by a single car
# costs induced when the car is not delivered at all (so the arrival date is assumed to be the end of the timeframe)
# computation for the case, where all cars are guaranteed to arrive is commented out
def simple_upper_bound(car, paths, segments):
    # determine latest possible arrival at the destination
    latest_arrival = end_of_timeframe(segments)
    # latest_arrival = car['avlDate']
    # for p in car['paths']:
    #     last_transport = paths[p][-1]
    #     last_departure = max(segments[last_transport]['timeslots'].keys())
    #     arrival = last_departure + timedelta(hours = segments[last_transport]['duration'])
    #     if arrival > latest_arrival:
    #         latest_arrival = arrival

    return compute_car_costs(car['avlDate'], car['dueDate'], latest_arrival, car['deliveryRef'])

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

# compute utilization of specific transports -> return value??
def compute_transport_usage(cars, segments):
    used_capacity = {}
    assignments = {}
    keys = [(s,t) for s in segments.keys() for t in segments[s]['timeslots'].keys()]
    for key in keys:
        assigned_cars = [id for id in cars.keys() if key in cars[id]['schedule']]
        used_capacity[key] = len(assigned_cars)
        assignments[key] = assigned_cars
    return used_capacity, assignments

# print the assignment of cars to transports
def print_transport_usage(cars, segments):
    used_capacities, assignments = compute_transport_usage(cars, segments)
    for s in segments.keys():
        print("-----------------------------------------")
        print(f"Segment {s}: {segments[s]['name']}")
        print("-----------------------------------------")
        for t in segments[s]['timeslots'].keys():
            free_capacity = int(segments[s]['timeslots'][t])
            used_capacity = used_capacities[(s,t)]
            if used_capacity != 0: # skip empty transports to save space
                print(f"{t}: {used_capacity}/{free_capacity+used_capacity} used | {assignments[(s,t)]}")
                print(".................................")

    return

# read the parsed data frames and
# transform relevant information into dictionaries for more comfortable access
# format: dictionary of dictionaries/lists
# car: {ID:int, avlDate:date, dueDate:date, paths:[int], assignedPath:int, currentDelivery:date, inducedCosts:int, costBound:int, deliveryRef: int}
# paths: {id:int, segments:[int]}
# segment: {id:int, timeslotsCaps:{date:int}, duration:int}
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
    # TODO: only keep paths from factories to dealers (-> relevant end-to-end connections)?
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
        departures = departures_df[departures_df['PathSegmentCode'] == code]
        for j in departures.index:
            date_string = departures['TimeSlotDate'][j]
            timeslots[handle_dates(date_string)] = float(departures['Capacity'][j])

        segment['timeslots'] = timeslots
        segments[id] = segment

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
        earliest_arrival = assign_timeslots(car, paths, segments)[2]
        ref = (earliest_arrival - car['avlDate']).total_seconds()/(60*60)
        car['deliveryRef'] = ref

        # lower bound for the costs
        car['costBound'] = simple_lower_bound(car, paths, segments)

        # set remaining values to default values (they are set during the algorithm)
        car['assignedPath'] = None
        car['currentDelivery'] = None
        car['schedule'] = None
        car['inducedCosts'] = 0

        cars[id] = car
    


    return cars, paths, segments

# greedy
def greedy(dataframes):
    cars, paths, segments = construct_instance(dataframes)
    eot = end_of_timeframe(segments)

    # replace "no deadline" with deadline eot TODO: mod in konstruktion der instanz, methoden anpassen
    for id in cars.keys():
        if cars[id]['dueDate'] == "-":
            cars[id]['dueDate'] = eot + timedelta(hours=24)

    # greedy algorithm -> variants
    car_list = sorted([(id, cars[id]['avlDate'], cars[id]['dueDate']) for id in cars.keys()], key=lambda car: (car[2],car[1])) # sort by duedate 
    # car_list = sorted([(id, cars[id]['avlDate'], cars[id]['dueDate']) for id in cars.keys()], key=lambda car: (car[1],car[2])) # sort by avldate 
    # car_list = sorted([(id, cars[id]['avlDate'], cars[id]['dueDate']) for id in cars.keys()], key=lambda car: (car[2]-car[1],car[2])) # sort by space (difference avl and due)
    # car_list = sorted([(id, simple_upper_bound(cars[id], paths, segments), cars[id]['dueDate']) for id in cars.keys()], key=lambda car: (car[1],car[2]), reverse=True) # sort descending by upper bound
    # car_list = sorted([(id, simple_upper_bound(cars[id], paths, segments)-simple_lower_bound(cars[id], paths, segments), cars[id]['dueDate']) for id in cars.keys()], key=lambda car: (car[1],car[2]), reverse=True) # sort descending by upper-lower bound

    # undo changes to not affect other methods
    for id in cars.keys():
        if cars[id]['dueDate'] == eot + timedelta(hours=24):
            cars[id]['dueDate'] = "-"

    # assign timeslots with earliest arrival
    for i in range(len(car_list)):
        id = car_list[i][0]
        d, p, a = assign_timeslots(cars[id], paths, segments)
        # link car to chosen path, save corresponding delivery date
        cars[id]['assignedPath'] = p
        cars[id]['currentDelivery'] = a

        # assign [(segID, time)] shaped schedule to car
        schedule = []
        path = paths[p] # path segments the car is assigned to 

        for s in range(len(path)):
            schedule.append((path[s], d[s]))
        cars[id]['schedule'] = schedule

        # block used capacities in transport segments (if a path was assigned)
        if p != None:
            for j in range(len(d)):
                segments[paths[p][j]]['timeslots'][d[j]] -= 1

    # detemine costs of the solution
    costs = 0
    for car_id in cars.keys():
        car_cost = compute_car_costs(cars[car_id]['avlDate'], cars[car_id]['dueDate'], cars[car_id]['currentDelivery'], cars[car_id]['deliveryRef'])
        cars[car_id]['inducedCosts'] = car_cost
        costs += car_cost
    
    return cars, paths, segments, costs

# as a randomized version of greedy or subroutine in local search
# exactly as greedy, but starts with a random ordering of the cars
def random_greedy(dataframes):
    cars, paths, segments = construct_instance(dataframes)

    # greedy algorithm -> variants
    car_list = [k for k in cars.keys()]
    random.shuffle(car_list) # random shuffle
    
    # assign timeslots with earliest arrival (maybe just earliest first departure or shortest net time?)
    for i in range(len(car_list)):
        id = car_list[i]
        d, p, a = assign_timeslots(cars[id], paths, segments)

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
       

    nd = 0 # for analysis: count non delivered cars
    for car_id in cars.keys():
            nd += 1

    # determine costs of the solution
    for car_id in cars.keys():
        car_cost = compute_car_costs(cars[car_id]['avlDate'], cars[car_id]['dueDate'], cars[car_id]['currentDelivery'], cars[car_id]['deliveryRef'])
        cars[car_id]['inducedCosts'] = car_cost
    
    return cars, paths, segments

# local search
def local_search(dataframes):
    cars, paths, segments, currentCost = random_greedy(dataframes) # start with the solution of the random greedy assignment

    swaps_made = 0 # for analysis: count successful swapping operations

    swap_candidates = [c for c in cars.keys() if cars[c]['inducedCosts'] > cars[c]['costBound']] # cars which currently have costs higher than their lower bound

    while swap_candidates != []:
        i = swap_candidates.pop(0)

        # cars to potentially swap with (same start- and endpoint, earlier arrival, compatible starttimes)
        partners = [c for c in cars.keys() if cars[c]['origin'] == cars[i]['origin'] and cars[c]['destination'] == cars[i]['destination'] and cars[c]['currentDelivery'] < cars[i]['currentDelivery']
                    and cars[c]['schedule'][0][1] >= cars[i]['avlDate'] and (cars[i]['assignedPath'] == None or cars[i]['schedule'][0][1] >= cars[c]['avlDate'])]
    
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

                currentCost -= diff # adjust current cost

                swaps_made += 1

                # update candidate list
                if new_costs_i > cars[i]['costBound']:
                    swap_candidates.append(i)
                if new_costs_p > cars[p]['costBound'] and p not in swap_candidates:
                    swap_candidates.append(p)
                break
 
    print(f"final costs: {currentCost}, swaps made: {swaps_made}")
    return cars, currentCost # maybe also segments..

# local search - 2nd draft
def advanced_local_search(dataframes):
    cars, paths, segments = random_greedy(dataframes) # start with the solution of the random greedy assignment
    currentCost = compute_total_costs(cars)
    swaps_made = 0 # for analysis: count successful swapping operations
    partials = 0 # swaps that did not swap full paths
    shifts = 0 # swaps to free paths

    swap_candidates = [c for c in cars.keys()] # all car ids

    while swap_candidates != []:
        i = swap_candidates.pop(0)

        # cars to potentially swap with (same destination and earlier arrival)
        partners = [c for c in cars.keys() if cars[c]['destination'] == cars[i]['destination'] and cars[c]['currentDelivery'] < cars[i]['currentDelivery']]
        swapped = False
        for p in partners:
            if cars[i]['assignedPath'] == None:
                checkpoints = 1
            else:
                path_segs = paths[cars[i]['assignedPath']]
                checkpoints = len(path_segs)
            # go over possible cuts..   
            for x in range(checkpoints):
                if x == 0:
                    earliest_start_i = cars[i]['avlDate']
                    start_location = cars[i]['origin']
                else:
                    # arrival of the x-1-th transport + waiting time
                    earliest_start_i = (cars[i]['schedule'][x-1][1] + timedelta(hours=24+segments[path_segs[x-1]]['duration'])).replace(hour=0, minute=0, second=0, microsecond=0)
                    start_location = segments[path_segs[x]]['start']

                # filter partners: their path contains the start location and the starting timeslots are compatible
                if start_location in [segments[s]['start'] for s in paths[cars[p]['assignedPath']]]:
                    index = [segments[s]['start'] for s in paths[cars[p]['assignedPath']]].index(start_location)
                    if x == 0:
                        earliest_start_p = cars[p]['avlDate']
                    else:
                        # arrival of the x-1-th transport + waiting time
                        earliest_start_p = (cars[p]['schedule'][index-1][1] + timedelta(hours=24+segments[path_segs[x-1]]['duration'])).replace(hour=0, minute=0, second=0, microsecond=0)

                    if (cars[i]['assignedPath'] == None or cars[i]['schedule'][x][1] >= earliest_start_p)and cars[p]['schedule'][index][1] >= earliest_start_i:

                        # check quality of swap
                        new_costs_i = compute_car_costs(cars[i]['avlDate'], cars[i]['dueDate'], cars[p]['currentDelivery'], cars[i]['deliveryRef'])
                        new_costs_p = compute_car_costs(cars[p]['avlDate'], cars[p]['dueDate'], cars[i]['currentDelivery'], cars[p]['deliveryRef'])

                        # difference: current costs - costs after swap
                        diff = cars[i]['inducedCosts'] + cars[p]['inducedCosts'] - (new_costs_i + new_costs_p)

                        if diff > 0: # if new costs are lower, swap chosen parts of p and i
                            temp = (cars[i]['schedule'], cars[i]['currentDelivery'])
                            cars[i]['schedule'] = cars[i]['schedule'][:x] + cars[p]['schedule'][index:]
                            cars[i]['currentDelivery'] = cars[p]['currentDelivery']
                            cars[i]['inducedCosts'] = new_costs_i
                            path_i = [path_index for path_index, path_segments in paths.items() if path_segments == [s for s,t in cars[i]['schedule']]][0]
                            cars[i]['assignedPath'] = path_i


                            cars[p]['schedule'] = cars[p]['schedule'][:index] + temp[0][x:]
                            cars[p]['currentDelivery'] = temp[1]
                            cars[p]['inducedCosts'] = new_costs_p
                            path_p = [path_index for path_index, path_segments in paths.items() if path_segments == [s for s,t in cars[p]['schedule']]]
                            if len(path_p) > 0:
                                cars[p]['assignedPath'] = path_p[0]
                            else:
                                cars[p]['assignedPath'] = None

                            currentCost -= diff # adjust current cost

                            swaps_made += 1
                            if x > 0:
                                partials += 1

                            # update candidate list
                            if new_costs_i > cars[i]['costBound']:
                                swap_candidates.append(i)
                            if new_costs_p > cars[p]['costBound'] and p not in swap_candidates:
                                swap_candidates.append(p)
                            swapped = True
                            break
        # if no partner works, try adjusting route using free capacities
        if not swapped:
            # free capacities currently used:
            for s,t in cars[i]['schedule']:
                segments[s]['timeslots'][t] += 1

            # check for an alternative free path
            departures, path, arrival = assign_timeslots(cars[i], paths, segments)

            if arrival < cars[i]['currentDelivery']:
                # link car to chosen path, save corresponding delivery date
                cars[i]['assignedPath'] = path
                cars[i]['currentDelivery'] = arrival

                # assign [(segID, time)] shaped schedule to car
                schedule = []
                path_segments = paths[path] # path segments the car is assigned to 

                for seg in range(len(path_segments)):
                    schedule.append((path_segments[seg], departures[seg]))
                cars[i]['schedule'] = schedule

                shifts += 1
                swaps_made += 1

                old_cost = cars[i]['inducedCosts']
                cars[i]['inducedCosts'] = compute_car_costs(cars[i]['avlDate'], cars[i]['dueDate'], cars[i]['currentDelivery'], cars[i]['deliveryRef'])
                currentCost -= (old_cost - cars[i]['inducedCosts'])
                
                # update candidate list
                if cars[i]['inducedCosts'] > cars[i]['costBound']:
                    swap_candidates.append(i)
            
            # block used capacities:
            for s,t in cars[i]['schedule']:
                segments[s]['timeslots'][t] -= 1


    print(f"final costs: {currentCost}, swaps made: {swaps_made}, patrials: {partials}, shifts: {shifts}")
    return cars, currentCost # maybe also segments..


###################### do stuff #######################
c,p,s=construct_instance(df)
eot = end_of_timeframe(s)

total_bound = 0
for car_id in c:
    total_bound += simple_lower_bound(c[car_id],p,s)
print(total_bound)

total_bound = 0
for car_id in c:
    total_bound += simple_upper_bound(c[car_id],p,s)
print(total_bound)

res = greedy(df)
print(f"result greedy: {res[3]}")
#local_search(df)
cs, cc = advanced_local_search(df)
print(f"sum over cars: {sum([cs[i]['inducedCosts'] for i in cs.keys()])}, compute function: {compute_total_costs(cs)}, return value: {cc}")

