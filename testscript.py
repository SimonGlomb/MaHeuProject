from monja_algorithms.greedy import greedy
from parse_txt import parse_file
import monja_preprocessing
from monja_evaluation import print_all_timetables, compute_total_costs
import argparse
import random
import time
import sys
import pickle

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input')
parser.add_argument('-r','--repetitions', default=1, type=int)
args = parser.parse_args()

file = args.input
i = 1
random.seed(0)

for x in range(i):
    df = parse_file(f"data\inst{file}.txt")
    cars, paths, segments, eot = monja_preprocessing.construct_instance(df)
    start_time = time.time()
    res = greedy(cars, paths, segments, eot)
    end_time = time.time()
    elapsed_time = end_time - start_time

    original_stdout = sys.stdout 
    with open(f'results\greedy_timetables_{file}.txt', 'w') as f:
        sys.stdout = f
        print_all_timetables(res[0], res[1])
        # Reset the standard output
        sys.stdout = original_stdout
    with open(f'results\greedy_time_{file}.txt', 'w') as f:
        sys.stdout = f
        print(f"elapsed time: {elapsed_time}")
        # Reset the standard output
        sys.stdout = original_stdout
    pickle.dump(res, open(f'results\greedy_result_{file}.txt', 'wb'))

cars, segments = pickle.load(open(f'results\greedy_result_{file}.txt', 'rb'))
print(compute_total_costs(cars))