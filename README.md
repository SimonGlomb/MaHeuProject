# MaHeuProject

How to contribute an optimization method:
1. Create a file in the folder "optimization_functions"
2. write a method "apply(result, dataframe)" with the following signature: "def apply(result: pd.DataFrame, dataframes: dict) -> Tuple[dict, dict]:"
3. The input is the result of preprocessing and parse_txt respectively
4. The output is the following: The first element is a dictionary which has as key the id of the car as string (e.g. "1") and the values are lists dictionaries ("PathSegmentCode": \<VALUE>, "TimeSlotDate": \<VALUE>, "LeadTimeHours": \<VALUE>); the second output is a dictionary with keys (PathSegmentCode, TimeSlotDate) and its values are another dictionary {"Capacity": \<VALUE>, "LeadTimeHours": \<VALUE>}
5. Implement the Algorithm
6. Import the file in "interface.py", and add it to the list of "choices=[...]" und the 'message="Select an optimization strategy"'