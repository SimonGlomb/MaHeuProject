# advanced local search approach: swapping only partial paths is allowed, swapping with free segments is also possible
# uses random greedy for the start solution

import random_greedy
from datetime import timedelta
from monja_evaluation import compute_car_costs
from monja_utility import earliest_timeslots_from_loc


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

# TODO: in general call use random.seed(0) in the beginning (just once). will allow to loop stuff and everything but reproducible