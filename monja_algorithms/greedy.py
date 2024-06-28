# greedy algorithm

from datetime import timedelta
from monja_utility import assign_timeslots



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
        if p != None:
            path = paths[p] # path segments the car is assigned to 
            for s in range(len(path)):
                schedule.append((path[s], d[s]))
        cars[id]['schedule'] = schedule

        # block used capacities in transport segments (if a path was assigned)
        if p != None:
            for j in range(len(d)):
                segments[paths[p][j]]['timeslots'][d[j]] -= 1
    
    return cars, segments
