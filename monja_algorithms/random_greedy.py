# subroutine for local search
# exactly as greedy, but starts with a random ordering of the cars

from monja_utility import assign_timeslots
from monja_evaluation import compute_car_costs
import random

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