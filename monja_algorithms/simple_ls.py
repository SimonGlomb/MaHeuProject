# simple local search approach: try to swap the paths of two cars with the same start and end location

from monja_evaluation import compute_car_costs, compute_total_costs
from monja_utility import random_greedy
import time

def local_search(cars, paths, segments, eot):
    # track development of solution quality over time
    times = []
    costs = []
    start_time = time.time()
    cars, segments = random_greedy(cars, paths, segments, eot) # start with the solution of the random greedy assignment
    solution_time = time.time()
    times.append(solution_time-start_time)
    costs.append(compute_total_costs(cars))

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

                    swapped = True
                    break
            if swapped:
                solution_time = time.time()
                times.append(solution_time-start_time)
                costs.append(compute_total_costs(cars))
                break

    return cars, segments, (times, costs)