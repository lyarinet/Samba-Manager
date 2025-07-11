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

# Create GoTTY config file
mkdir -p ~/.gotty
cat > ~/.gotty/config.toml << EOL
port = 8080
permit_write = true
width = 0
height = 0
title_format = "Terminal - Samba Manager"
enable_resize = true
EOL

# Kill any existing GoTTY processes
pkill -f "gotty -w"

# Start GoTTY with bash in the background
echo "Starting terminal service on port 8080..."
$(go env GOPATH)/bin/gotty -w bash &

echo "Terminal service started. You can access it at: http://localhost:8080" 