from algorithms.greedy import greedy
from algorithms.simple_ls import local_search
from algorithms.advanced_ls import advanced_local_search
from parse_txt import parse_file
import preprocessing
from evaluation import print_all_timetables, compute_total_costs, print_transport_usage
import argparse
import random
import time
import sys
import pickle

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input', help ="the instance number (for example \"005a\")")
parser.add_argument('-a', '--algorithm',choices=["greedy", "local_search", "advanced_local_search"], help= "The algorithm to apply")
parser.add_argument('-r', '--repetitions', type=int, default=1, help="the number of repetitions to run (for example for algorithms with a random start solution)")
args = parser.parse_args()

instance = args.input
iterative = False
# switch for algortithm parameter
match args.algorithm:
    case "greedy":
        algo = greedy
        short_name = "greedy"
        long_name = "greedy algorithm"
    case "local_search":
        iterative = True
        algo = local_search
        short_name = "sls"
        long_name = "simple local search algorithm"
    case "advanced_local_search":
        iterative = True
        algo = advanced_local_search
        short_name = "als"
        long_name = "advanced local search algorithm"

repetitions = args.repetitions
# loop function -> results as arrays, uniform names

random.seed(0)
df = parse_file(f"data\inst{instance}.txt")

if repetitions == 1:
    cars, paths, segments, eot = preprocessing.construct_instance(df)
    start_time = time.time()
    res = algo(cars, paths, segments, eot)
    end_time = time.time()
    elapsed_time = end_time - start_time
    cost = compute_total_costs(res[0])

    # print results
    print(f"{long_name} on instance {instance}:")
    print(f"final cost: {cost}, total time: {elapsed_time}s")
    print(f"{len([id for id in res[0].keys() if res[0][id]['assignedPath'] == None])} of the {len(cars.keys())} cars are not delivered in the final solution.")

    # save results for later use
    original_stdout = sys.stdout 
    with open(f'results\schedules_{short_name}_{instance}.txt', 'w') as f: # save the routing information for each car
        sys.stdout = f
        print_all_timetables(res[0], res[1])

    with open(f'results\carsAtTransport_{short_name}_{instance}.txt', 'w') as f: # save the assignment of cars to transports
        sys.stdout = f
        print_transport_usage(res[0], res[1])
        sys.stdout = original_stdout


    pickle.dump((elapsed_time, cost), open(f'results\outcome_{short_name}_{instance}.txt', 'wb')) # save tuple (time, cost)
    pickle.dump((res[0], res[1]), open(f'results\mapping_{short_name}_{instance}.txt', 'wb')) # save the cars- and segments objects for later analysis
    if iterative:
        pickle.dump(res[2], open(f'results\development_{short_name}_{instance}.txt', 'wb')) # save tuple (times, costs) with the development of the solution over time

else: # more than one repetition -> store all results as lists for analysis, present best solution
    times = []
    costs = []
    mappings = []
    if iterative:
        developments = []
    best_solution_index = -1 # track position of best solution found

    for i in range(repetitions):
        cars, paths, segments, eot = preprocessing.construct_instance(df)
        start_time = time.time()
        res = algo(cars, paths, segments, eot)
        end_time = time.time()
        cost = compute_total_costs(res[0])
        if len(costs) == 0 or cost < costs[-1]:
            best_solution_index = i
        times.append(end_time-start_time)
        costs.append(cost)
        mappings.append((res[0], res[1]))
        if iterative:
            developments.append(res[2])
    print(f"best solution for instance {instance} with {long_name} (found in iteration {best_solution_index+1} of {repetitions}):")
    print(f"cost: {costs[best_solution_index]}, time: {times[best_solution_index]}s")
    print(f"{len([id for id in mappings[best_solution_index][0].keys() if mappings[best_solution_index][0][id]['assignedPath'] == None])} of the {len(cars.keys())} cars are not delivered in this solution.")

    pickle.dump((times, costs), open(f'results\outcomes_{repetitions}_{short_name}_{instance}.txt', 'wb')) # save tuple (times, costs)
    pickle.dump(mappings, open(f'results\mappings_{repetitions}_{short_name}_{instance}.txt', 'wb')) # save the cars- and segments objects for later analysis
    if iterative:
        pickle.dump(developments, open(f'results\developments_{repetitions}_{short_name}_{instance}.txt', 'wb')) # save tuple (times, costs) with the development of the solution over time
