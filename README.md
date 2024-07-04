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

# Running algorithms
In order to execute one of the algorithms on a specific instance, run:  
`testscript.py [-h] [-i INPUT] [-a {greedy,local_search,advanced_local_search}] [-r REPETITIONS]`  
`-h` displays the help, ´-i´ specifies the input file (just the number, for example '002a' for inst002a), `-a` the algorithm (as specified in the list of choices) and `-r` the number of repetitions.  
The script will execute the algorithm on the instance and display some information, like the total runtime and the final solution costs. By default the number of repetitions is 1. If a higher number of repetitions is requested, the results of the best run are displayed. In any case the results (runtime, schedules, final and intermediate costs) are stored for later use (see following section).  
**Note:** The input files need to be placed in the *data*-directory. Also the file paths in the script may not work in linux systems (backslashes have to be replaced with slashes).
# Storage of results
