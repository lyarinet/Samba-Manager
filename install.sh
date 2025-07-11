#!/bin/bash
#
# Samba Manager Installation Script
#

# Check if script is running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root. Please use sudo."
   exit 1
fi

echo "=========================================================="
echo "        Samba Manager Installation Script"
echo "=========================================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Installing..."
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
else
    echo "Python 3 is already installed."
fi

# Check if Samba is installed
if ! command -v smbd &> /dev/null; then
    echo "Samba is not installed. Installing..."
    apt-get update
    apt-get install -y samba samba-common smbclient
else
    echo "Samba is already installed."
fi

# Create smbusers group if it doesn't exist
if ! getent group smbusers > /dev/null; then
    echo "Creating smbusers group..."
    groupadd smbusers
else
    echo "smbusers group already exists."
fi

# Install directory
INSTALL_DIR="/opt/samba-manager"
echo "Installing Samba Manager to $INSTALL_DIR..."

# Create installation directory
mkdir -p $INSTALL_DIR

# Copy all files to installation directory
cp -r * $INSTALL_DIR

# Create a virtual environment
echo "Creating Python virtual environment..."
cd $INSTALL_DIR
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create a systemd service file
echo "Creating systemd service file..."
cat > /etc/systemd/system/samba-manager.service << EOF
[Unit]
Description=Samba Manager Web Interface
After=network.target

[Service]
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run.py --port 5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create a convenient run script
echo "Creating run script..."
cat > /usr/local/bin/samba-manager << EOF
#!/bin/bash
cd $INSTALL_DIR
./run_with_sudo.sh
EOF
chmod +x /usr/local/bin/samba-manager

# Reload systemd, enable and start the service
echo "Enabling and starting Samba Manager service..."
systemctl daemon-reload
systemctl enable samba-manager.service
systemctl start samba-manager.service

echo ""
echo "=========================================================="
echo "        Samba Manager Installation Complete!"
echo "=========================================================="
echo ""
echo "The Samba Manager web interface is running at:"
echo "http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "Default login credentials:"
echo "Username: admin"
echo "Password: admin"
echo ""
echo "IMPORTANT: Change the default password after your first login!"
echo ""
echo "To control the service:"
echo "  Start:   systemctl start samba-manager.service"
echo "  Stop:    systemctl stop samba-manager.service"
echo "  Restart: systemctl restart samba-manager.service"
echo "  Status:  systemctl status samba-manager.service"
echo ""
echo "To run Samba Manager manually, use:"
echo "  samba-manager"
echo ""
echo "Installation directory: $INSTALL_DIR"
echo "==========================================================" 