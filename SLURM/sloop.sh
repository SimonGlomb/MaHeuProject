#!/usr/local_rwth/bin/zsh

instances=("001" "002a" "002b" "002c" "003" "004" "005a" "005b" "006a" "006b" "006c" "006d" "006e" "006f" "006g")
algos=("greedy" "local_search" "advanced_local_search")

for algo in ${algos[@]}
do
    for instance in ${instances[@]}
    do
        sbatch slurm.sh $algo $instance
    done
done