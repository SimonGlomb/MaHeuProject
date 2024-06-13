import os
import inquirer
import time
import csv

import parse_txt
import preprocessing
from optimization_functions import greedy_algorithm
import evaluation


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


    answers = inquirer.prompt(questions)

    # Print the selected file
    selected_file = answers["file"]
    selected_function = answers["function"]
    dataframes = parse_txt.parse_file("./data/" + selected_file)
    result = preprocessing.convert_to_dataframe(dataframes)
    execution_data = [questions[1].choices[0]]    

    start_time = time.time()
    mapping = selected_function.apply(result, dataframes)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"The algorithm took {elapsed_time:.2f} seconds to run")
    execution_data.append(elapsed_time)

    costs = evaluation.compute_costs_of_mapping(mapping, dataframes)
    execution_data.append(costs)

    csv_file = "./results.csv"

    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        file_exists = os.path.isfile(csv_file)
        file_empty = os.stat(csv_file).st_size == 0 if file_exists else True
        if not file_exists or file_empty:
            writer.writerow(["Algorithm", "Time", "Costs"])
        writer.writerow(execution_data)

    

if __name__ == '__main__':
    main()