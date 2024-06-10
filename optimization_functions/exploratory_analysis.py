from preprocessing import result, dataframes
import pandas as pd

def filter_dataframe(df):
    # Replace "-" with NaT
    df['DueDateDestinaton'] = df['DueDateDestinaton'].replace('-', pd.NaT)
    # Convert date columns from strings to datetime objects
    df['DueDateDestinaton'] = pd.to_datetime(df['DueDateDestinaton'], format='%d/%m/%Y-%H:%M:%S')
    df['TimeSlotDate'] = pd.to_datetime(df['TimeSlotDate'], format='%d/%m/%Y-%H:%M:%S')
    # make string of e.g. 72.0 to a numeric
    df['LeadTimeHours'] = pd.to_numeric(df['LeadTimeHours'])
    # Convert LeadTimeHours to time difference
    df['LeadTimeHours'] = pd.to_timedelta(df['LeadTimeHours'], unit='h')
    # Calculate the threshold date
    df['ThresholdDate'] = df['TimeSlotDate'] + df['LeadTimeHours']
    # Filter the DataFrame
    # keep rows which have NaT, i.e. they had "-" before and so no DueDateDestinaton
    filtered_df = df[(df['DueDateDestinaton'].isna()) | (df['DueDateDestinaton'] < df['ThresholdDate'])]
    # Drop the ThresholdDate column as it's no longer needed
    filtered_df = filtered_df.drop(columns=['ThresholdDate'])
    return filtered_df

#### EXPLORATORY PART OF THE SPECIFIC DATASET
def check_unique_path_segment_codes(df):
    # Group by "ID(long)" and count unique "PathSegmentCode" entries
    unique_counts = df.groupby('ID(long)')['PathSegmentCode'].nunique()
    # Check if each count is exactly 2
    valid_ids = unique_counts[unique_counts == 2].index
    # Find IDs with not exactly 2 unique PathSegmentCode entries
    non_valid_ids = unique_counts[unique_counts != 2].index
    # Check if all IDs are valid
    all_valid = len(non_valid_ids) == 0
    return all_valid, list(non_valid_ids)

segments_without_time_violations = filter_dataframe(result)
## When looking at the result after filtering, we still have all 50 cars. And for each of them we still have both of the path segments needed. So if there would be no capacities, it is possible to deliver all in time
## segments_without_time_violations["ID(long)"].nunique()
## one can check that all of them have both path segments by check_unique_path_segment_codes(segments_without_time_violations)

result_sorted_destination = segments_without_time_violations.sort_values(by='DueDateDestinaton')
result_sorted_time_slot_transport = segments_without_time_violations.sort_values(by='TimeSlotDate')

for el in dataframes["PTR"]:
    print(el)
breakpoint()

print(result)