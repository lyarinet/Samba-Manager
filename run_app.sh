#!/bin/bash
# Script to run the Samba Manager application

# Check if Python 3 is installed
if command -v python3 &>/dev/null; then
  PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
  PYTHON_CMD="python"
else
  echo "Error: Python not found. Please install Python 3."
  exit 1
fi

# Check if Samba is installed
if ! command -v smbd &>/dev/null; then
  echo "Warning: Samba is not installed or not in PATH."
  echo "For full functionality, please run: sudo ./setup_samba.sh"
  echo "Continuing in development mode..."
fi

# Check if shares.conf exists
if [ ! -f "/etc/samba/shares.conf" ]; then
  echo "Warning: /etc/samba/shares.conf not found."
  echo "For full functionality, please run: sudo ./setup_samba.sh"
  echo "Continuing in development mode..."
fi

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  $PYTHON_CMD -m venv venv
  if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment. Make sure python3-venv is installed."
    echo "Try: sudo apt-get install python3-venv"
    exit 1
  fi
fi

# Activate virtual environment and install dependencies
echo "Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Start terminal service
echo "Starting terminal service..."
./start_terminal_service.sh

# Check if app is running with sudo
if [ "$EUID" -eq 0 ]; then
  echo "Running in production mode with sudo..."
  export SAMBA_MANAGER_DEV_MODE=0
else
  echo "Running in development mode..."
  export SAMBA_MANAGER_DEV_MODE=1
fi

# Run the application
echo "Starting Samba Manager..."
$PYTHON_CMD run.py 