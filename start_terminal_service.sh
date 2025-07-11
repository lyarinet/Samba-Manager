#!/bin/bash

# Check if GoTTY is installed
if ! command -v gotty &> /dev/null; then
    echo "GoTTY is not installed. Installing..."
    
    # Check if Go is installed
    if ! command -v go &> /dev/null; then
        echo "Go is not installed. Installing..."
        sudo apt update
        sudo apt install -y golang-go
    fi
    
    # Install GoTTY
    go install github.com/sorenisanerd/gotty@latest
    
    # Add Go bin to PATH for this session
    export PATH=$PATH:$(go env GOPATH)/bin
fi

# Remove existing config if it exists
if [ -e ~/.gotty ]; then
    rm -rf ~/.gotty
fi

# Kill any existing GoTTY processes
pkill -f "gotty" 2>/dev/null || true

# Get the server's IP address
SERVER_IP=$(hostname -I | awk '{print $1}')

# Start GoTTY with bash in the background, explicitly binding to all interfaces
echo "Starting terminal service on port 8080..."
$(go env GOPATH)/bin/gotty -w --address 0.0.0.0 --port 8080 bash &

echo "Terminal service started. You can access it at: http://${SERVER_IP}:8080" 