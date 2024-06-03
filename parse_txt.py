import pandas as pd
import re

def parse_file(file_path):
    data = {}
    columns = {}
    sections = set()
    current_section = None

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip() # so that \n is removed
            if line.startswith('#'):

                match = re.match(r'#(\w+)-(.*)', line)
                if match:
                    current_section = match.group(1) # e.g. LOC, MOD, SEG, PTH, ...
                    sections.add(current_section)
                    col_names = match.group(2).split(';') # the column names
                    columns[current_section] = col_names
                    data[current_section] = []
            else:
                match = re.match(r'(\w+);(.*)', line)
                current_section = match.group(1)
                data[current_section].append(line.split(';'))
    dataframes = {section: pd.DataFrame(rows, columns=columns[section]) for section, rows in data.items() if rows}

    return dataframes

file_path = './data/inst001.txt'
dataframes = parse_file(file_path)

for section, df in dataframes.items():
    print(f"{section} DataFrame:")
    print(df)
    print()