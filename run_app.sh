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

# Check if app is running with sudo
if [ "$EUID" -eq 0 ]; then
  echo "Running in production mode with sudo..."
  # Set DEV_MODE to False in samba_utils.py
  sed -i 's/DEV_MODE = True/DEV_MODE = False/g' app/samba_utils.py
else
  echo "Running in development mode..."
  # Set DEV_MODE to True in samba_utils.py
  sed -i 's/DEV_MODE = False/DEV_MODE = True/g' app/samba_utils.py
fi

# Run the application
echo "Starting Samba Manager..."
$PYTHON_CMD run.py 