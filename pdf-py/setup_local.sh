#!/bin/bash
set -e

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Run the application
python app.py


# To profile the application
# python -m cProfile -o program.prof app.py
# snakeviz program.prof
