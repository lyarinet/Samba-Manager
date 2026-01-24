#!/bin/bash

# Path to the virtual environment's Python interpreter
VENV_PYTHON="$PWD/venv/bin/python"

# Set development mode
export SAMBA_MANAGER_DEV_MODE=0

# Use port 5000 for the web interface
export FLASK_PORT=5000

# Check if network access fix script exists and is executable
if [ -f "fix_network_access.sh" ]; then
    echo "Checking network access configuration..."
    
    # Make it executable if it's not already
    if [ ! -x "fix_network_access.sh" ]; then
        chmod +x fix_network_access.sh
    fi
    
    # Run the network access fix script
    sudo ./fix_network_access.sh
else
    # Start terminal service directly if fix script doesn't exist
    echo "Starting terminal service..."
    ./start_terminal_service.sh
fi

# Get the server's IP address
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Server IP: $SERVER_IP"
echo "Web interface will be available at: http://$SERVER_IP:$FLASK_PORT"
echo "Terminal service will be available at: http://$SERVER_IP:8080"

# Run the application with sudo, preserving the environment and using the venv Python
sudo -E $VENV_PYTHON run.py --host 0.0.0.0 --port $FLASK_PORT 