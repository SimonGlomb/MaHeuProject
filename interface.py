import parse_txt
import preprocessing
from optimization_functions import greedy_algorithm
import evaluation

def main():
    dataframes = parse_txt.parse_file('./data/inst001.txt')
    #dataframes = parse_txt.parse_file('./data/inst002a.txt')
    #dataframes = parse_txt.parse_file('./data/inst002b.txt')
    #dataframes = parse_txt.parse_file('./data/inst002c.txt')
    #dataframes = parse_txt.parse_file('./data/inst003.txt')
    result = preprocessing.convert_to_dataframe(dataframes)
    
    mapping, path_segment_dict = greedy_algorithm.apply(result, dataframes)

    print("Costs:")
    print(evaluation.compute_costs_of_mapping(mapping, path_segment_dict, dataframes))

if __name__ == '__main__':
    main()