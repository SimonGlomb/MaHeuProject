# MaHeuProject

## How To Use

1. Put according data in the directory "data"
2. Run the interface: "python .\interface.py"
3. Select dataset and algorithm
4. Profit

## How To Contribute
How to contribute an optimization method:
1. Create a file in the folder "optimization_functions"
2. write a method "apply(result, dataframe)" with the following signature: "def apply(result: pd.DataFrame, dataframes: dict) -> Tuple[dict, dict]:"
   -  The input is the result of preprocessing and parse_txt respectively
   - The output is the following: A dictionary which has as key the id of the car as string (e.g. "1") and the values are lists dictionaries ("PathSegmentCode": \<VALUE>, "TimeSlotDate": \<VALUE>, "LeadTimeHours": \<VALUE>)
3. Implement the Algorithm
4. Import the file in "interface.py", and add it to the list of "choices=[...]" under the 'message="Select an optimization strategy"'

Notably, there are functions available in the file "utility.py" which may be useful for your algorithm.

The results of each execution are saved in a "results.csv" file.