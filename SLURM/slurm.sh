#!/usr/local_rwth/bin/zsh
#
#SBATCH --output=output_%jx.txt
#SBATCH --time=10:00:00
#SBATCH --mem-per-cpu=2500M
#
#SBATCH --mail-type=ALL
#SBATCH --mail-user=monja.raschke@rwth-aachen.de
module --ignore_cache load "GCCcore/.12.2.0"
module --ignore_cache load "Python/3.10.8"
python3 testscript.py -i $2 -a $1
