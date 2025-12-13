#!/usr/bin/env bash -l

# Get the absolute path of the parent directory
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIR_ROOT=$(pwd)

# Add the project root to PYTHONPATH
export PYTHONPATH=$DIR_ROOT:$PROJECT_ROOT:$PYTHONPATH

# Print confirmation
echo "Added $PROJECT_ROOT to PYTHONPATH"
echo "Current PYTHONPATH: $PYTHONPATH"

# Check if conda environment exists
if ! conda env list | grep -q "^recipe_engine_env "; then
    echo "Creating conda environment 'recipe_engine_env'..."
    conda create -n recipe_engine_env python=3.10 -y
    conda activate recipe_engine_env
else
    echo "Conda environment 'recipe_engine_env' already exists."
    conda activate recipe_engine_env
fi

echo "Installing requirements..."
python3 -m pip install -r requirements.txt
