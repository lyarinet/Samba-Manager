#!/bin/bash

# Path to the virtual environment's Python interpreter
VENV_PYTHON="$PWD/venv/bin/python"

# Set development mode
export SAMBA_MANAGER_DEV_MODE=0

# Use port 5002 to avoid conflicts
export FLASK_PORT=5002

# Start terminal service
echo "Starting terminal service..."
./start_terminal_service.sh

# Run the application with sudo, preserving the environment and using the venv Python
sudo -E $VENV_PYTHON run.py 