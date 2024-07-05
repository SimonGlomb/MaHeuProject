# MaHeu Project

## depencies

    python 3.10.8
    pandas
    argparse
    datetime
    time
    math
    pickle
    matplotlib
    re
# Repository structure
The *data*-directory contains the provided test instances, the algorithms are implemented in seperate files in the *algorithms* directory. The files *preprocessing.py, parse_txt.py, utility.py* and *evaluation.py* contain auxiliary functions to read and process the data from the provided instance files and analyze the outputs of the algorithms. With *testscript.py* you can execute an algorithm on a selected inputfile. The results from this are stored in the *results*-directory. The *study_results*-directory contains the data derived during our computational study.
# Running algorithms
In order to execute one of the algorithms on a specific instance, run:  
`testscript.py [-h] [-i INPUT] [-a {greedy,local_search,advanced_local_search}] [-r REPETITIONS]`  
`-h` displays the help, ´-i´ specifies the input file (just the number, for example '002a' for inst002a), `-a` the algorithm (as specified in the list of choices) and `-r` the number of repetitions.  
The script will execute the algorithm on the instance and display some information, like the total runtime and the final solution costs. By default the number of repetitions is 1. If a higher number of repetitions is requested, the results of the best run are displayed. In any case the results (runtime, schedules, final and intermediate costs) are stored for later use (see following section).  
**Note:** The input files need to be placed in the *data*-directory. Also the file paths in the script may not work in linux systems (backslashes have to be replaced with slashes).
# Storage of results
When running *testscript.py* we store the following information as pickle-files. The 'input' in the file names is the same as for the calling of the script. The 'algorithm' is a short form (greedy, sls, als):  
- the tuple (total time, final costs) in the file *results\outcome_{algorithm}_{input}.txt*
- the tuple (cars, segments) in the file *results\mapping_{algorithm}_{input}.txt*; these are dictionaries used in the algorithms and later analyses and contain among other things the routing information and the remaining capacities
  
If a local search variant is used (the solution develops over multiple iterations) we additionally store:

- the tuple (times, costs) in the file *results\development_{algorithm}_{input}.txt*; where times is a list of the times (in seconds from start of the algorithm) after which a new solution was found and costs a list with the corresponding objective values  

If more than one repetition is run, the same data is stored, but in lists, with one element for each iteration. The stored files additionally have the number of repetitions in their name,  
for example *results\developments_{repetitions}\_{algorithm}_{input}.txt*  
If only a single iteration is run, we additionally store two readable versions of the schedule as text-files:  
- *results\schedules_{algorithm}_{instance}.txt* is the routing information for each car
- *results\carsAtTransport_{algorithm}_{input}.txt* is the utilization of the transports
