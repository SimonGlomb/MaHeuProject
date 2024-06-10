import pandas as pd
import re

def parse_file(file_path):
    data = {}
    columns = {}
    # safe all types and use the keyword of the first column to determine in which dataframe
    # necessary as sometimes two types and their columns are explained right after each other
    types = set()
    current_type = None

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip() # so that \n is removed
            if line.startswith('#'):

                match = re.match(r'#(\w+)-(.*)', line)
                if match:
                    current_type = match.group(1) # e.g. LOC, MOD, SEG, PTH, ...
                    types.add(current_type)
                    col_names = match.group(2).split(';') # the column names
                    columns[current_type] = col_names
                    data[current_type] = []
            else:
                match = re.match(r'(\w+);(.*)', line)
                current_type = match.group(1)
                data[current_type].append(line.split(';'))
    dataframes = {section: pd.DataFrame(rows, columns=columns[section]) for section, rows in data.items() if rows}

    return dataframes