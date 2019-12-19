# PacManSolver

Python2 required!

## Optional
Use pipenv to ensure python2. Ensure installed `pipenv --version`. If not, find instructions at: https://github.com/pypa/pipenv#installation
```
pipenv shell
```

## Run
```
cd src
python pacman.py -p <agent-name> -l <layout-name> [-n <number-of-runs>] [-t or -q] 
```

## Commands
```
python pacman.py -p MDPAgent -l smallGrid -n 10 -q
python pacman.py -p MDPAgent -l mediumClassic -n 10 -q
```