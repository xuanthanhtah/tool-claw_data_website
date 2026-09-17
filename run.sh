#!/bin/bash

# VinFast Scraper Quick Runner Script

# Get script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    playwright install chromium
else
    source .venv/bin/activate
fi

# Run python script with arguments passed to run.sh
python main.py "$@"
