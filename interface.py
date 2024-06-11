import os
import inquirer

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
    
    mapping, path_segment_dict = selected_function.apply(result, dataframes)

    print("Costs:")
    print(evaluation.compute_costs_of_mapping(mapping, path_segment_dict, dataframes))

if __name__ == '__main__':
    main()