import os
import inquirer
import time
import csv
from pprint import pprint

import parse_txt
import preprocessing
from optimization_functions import greedy_algorithm
import evaluation
from utility import all_cars_have_path_without_gaps_from_origin_to_destination


def main():
    files = os.listdir("./data")
    if not files:
        print(f"No files found.")
        exit(1)
    questions = [
        inquirer.List(
            "file",
            message="Select a file",
            choices=files,
        ),
        inquirer.List(
            "function",
            message="Select an optimization strategy",
            choices=[greedy_algorithm]
        )
    ]

    execution_data = []
    
    answers = inquirer.prompt(questions)

    # Print the selected file
    selected_file = answers["file"]
    selected_function = answers["function"]
    dataframes = parse_txt.parse_file("./data/" + selected_file)
    result = preprocessing.convert_to_dataframe(dataframes)
    execution_data.append(answers["file"])
    execution_data.append(answers["function"])

    start_time = time.time()
    mapping = selected_function.apply(result, dataframes)
    end_time = time.time()
    elapsed_time = end_time - start_time
    pprint(mapping)
    print(f"The algorithm took {elapsed_time:.2f} seconds to run")
    execution_data.append(elapsed_time)

    if not all_cars_have_path_without_gaps_from_origin_to_destination(car_ids=dataframes["TRO"]["ID(long)"].unique(), car_to_path_segment_mapping=mapping, dataframes=dataframes):
        print("The solution is not valid! Not all cars get to their destination without gaps!")

    costs = evaluation.compute_costs_of_mapping(mapping, dataframes)
    execution_data.append(costs)

    csv_file = "./results.csv"

    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        file_exists = os.path.isfile(csv_file)
        file_empty = os.stat(csv_file).st_size == 0 if file_exists else True
        if not file_exists or file_empty:
            writer.writerow(["Data", "Algorithm", "Time", "Costs"])
        writer.writerow(execution_data)

    

if __name__ == '__main__':
    main()