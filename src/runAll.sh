#! bin/bash

date > log.log
for fp in $(seq 0.00 0.01 0.15);
do
  echo   "Case S+Si with Si%wt at "$fp                      >> log.log
  echo   "margot S+Si Steinbruegge"                         >> log.log
  date                                                      >> log.log
  python -u  main.py 'p' 'margot' 'S+Si' 'Steinbruegge' $fp >> log.log
  echo   "genova S+Si Steinbruegge"                         >> log.log
  date                                                      >> log.log 
  python -u main.py 'p' 'genova' 'S+Si' 'Steinbruegge' $fp  >> log.log
  echo   "margot S+Si Edmund"                               >> log.log
  date                                                      >> log.log
  python -u main.py 'p' 'margot' 'S+Si' 'Edmund' $fp        >> log.log
  echo   "genova S+Si Edmund"                               >> log.log
  date                                                      >> log.log
  python -u main.py 'p' 'genova' 'S+Si' 'Edmund' $fp        >> log.log
done  

python main.py 'p' 'margot' 'S' 'Steinbruegge' >> log.log
python main.py 'p' 'margot' 'Si' 'Steinbruegge' >> log.log
python main.py 'p' 'genova' 'S' 'Steinbruegge' >> log.log
python main.py 'p' 'genova' 'Si' 'Steinbruegge' >> log.log
python main.py 'p' 'margot' 'S' 'Edmund' >> log.log
python main.py 'p' 'margot' 'Si' 'Edmund' >> log.log
python main.py 'p' 'genova' 'S' 'Edmund' >> log.log
python main.py 'p' 'genova' 'Si' 'Edmund' >> log.log

