#!/bin/bash
#
# Samba Manager Network Access Fix Script
#

# Check if script is running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root. Please use sudo."
   exit 1
fi

echo "=========================================================="
echo "        Samba Manager Network Access Fix"
echo "=========================================================="
echo ""

# Get the server's IP address
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Server IP: $SERVER_IP"

# Update the systemd service file to explicitly bind to all interfaces
echo "Updating Samba Manager service configuration..."
cat > /etc/systemd/system/samba-manager.service << EOF
[Unit]
Description=Samba Manager Web Interface
After=network.target

[Service]
User=root
WorkingDirectory=/opt/samba-manager
ExecStart=/opt/samba-manager/venv/bin/python /opt/samba-manager/run.py --host 0.0.0.0 --port 5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and restart the service
echo "Reloading systemd and restarting Samba Manager service..."
systemctl daemon-reload
systemctl restart samba-manager.service

# Check if the service is running
if systemctl is-active --quiet samba-manager.service; then
    echo "Samba Manager service is running."
else
    echo "Warning: Samba Manager service is not running. Please check the logs."
fi

# Check if UFW is active
if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
    echo "Configuring UFW firewall..."
    # Allow Samba Manager web interface
    ufw allow 5000/tcp
    # Allow terminal service
    ufw allow 8080/tcp
    # Allow Samba
    ufw allow Samba
    echo "Firewall configured."
fi

# Check if firewalld is active
if command -v firewall-cmd &> /dev/null && firewall-cmd --state | grep -q "running"; then
    echo "Configuring firewalld..."
    # Allow Samba Manager web interface
    firewall-cmd --permanent --add-port=5000/tcp
    # Allow terminal service
    firewall-cmd --permanent --add-port=8080/tcp
    # Allow Samba
    firewall-cmd --permanent --add-service=samba
    firewall-cmd --reload
    echo "Firewall configured."
fi

# Fix terminal service
echo "Updating terminal service configuration..."
cat > /opt/samba-manager/start_terminal_service.sh << EOF
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
    export PATH=\$PATH:\$(go env GOPATH)/bin
fi

# Remove existing config if it exists
if [ -e ~/.gotty ]; then
    rm -rf ~/.gotty
fi

# Kill any existing GoTTY processes
pkill -f "gotty" 2>/dev/null || true

# Get the server's IP address
SERVER_IP=\$(hostname -I | awk '{print \$1}')

# Start GoTTY with bash in the background, explicitly binding to all interfaces
echo "Starting terminal service on port 8080..."
\$(go env GOPATH)/bin/gotty -w --address 0.0.0.0 --port 8080 bash &

echo "Terminal service started. You can access it at: http://\${SERVER_IP}:8080"
EOF

# Make the script executable
chmod +x /opt/samba-manager/start_terminal_service.sh

# Restart terminal service
echo "Restarting terminal service..."
pkill -f "gotty" 2>/dev/null || true
/opt/samba-manager/start_terminal_service.sh

echo ""
echo "=========================================================="
echo "        Network Access Fix Complete"
echo "=========================================================="
echo ""
echo "Samba Manager web interface should now be accessible at:"
echo "http://$SERVER_IP:5000"
echo ""
echo "Terminal service should now be accessible at:"
echo "http://$SERVER_IP:8080"
echo ""
echo "If you still have connection issues, please check your network"
echo "configuration and ensure there are no other firewalls blocking access."
echo "==========================================================" 