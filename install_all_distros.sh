#!/bin/bash
#
# Samba Manager Universal Installation Script
# Supports Ubuntu/Debian, Fedora/RHEL, and Arch Linux
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

# Detect the Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    DISTRO_FAMILY=$ID_LIKE
    echo "Detected distribution: $DISTRO"
else
    echo "Cannot detect Linux distribution. Exiting."
    exit 1
fi

# Install dependencies based on the distribution
install_dependencies() {
    echo "Installing dependencies..."
    
    # Ubuntu/Debian based systems
    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" || "$DISTRO_FAMILY" == *"debian"* ]]; then
        apt-get update
        apt-get install -y python3 python3-pip python3-venv samba samba-common smbclient
    
    # Fedora/RHEL based systems
    elif [[ "$DISTRO" == "fedora" || "$DISTRO" == "rhel" || "$DISTRO" == "centos" || "$DISTRO_FAMILY" == *"fedora"* || "$DISTRO_FAMILY" == *"rhel"* ]]; then
        dnf update -y
        dnf install -y python3 python3-pip samba samba-client
    
    # Arch Linux
    elif [[ "$DISTRO" == "arch" || "$DISTRO" == "manjaro" || "$DISTRO_FAMILY" == *"arch"* ]]; then
        pacman -Syu --noconfirm
        pacman -S --noconfirm python python-pip samba
    
    else
        echo "Unsupported distribution: $DISTRO"
        echo "Please install the following packages manually:"
        echo "- Python 3"
        echo "- pip"
        echo "- Samba"
        read -p "Press Enter to continue after installing these packages..."
    fi
}

# Create smbusers group
create_smbusers_group() {
    echo "Setting up smbusers group..."
    if ! getent group smbusers > /dev/null; then
        groupadd smbusers
    else
        echo "smbusers group already exists."
    fi
}

# Install Samba Manager
install_samba_manager() {
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
}

# Create systemd service
create_systemd_service() {
    echo "Creating systemd service file..."
    cat > /etc/systemd/system/samba-manager.service << EOF
[Unit]
Description=Samba Manager Web Interface
After=network.target

[Service]
User=root
WorkingDirectory=/opt/samba-manager
ExecStart=/opt/samba-manager/venv/bin/python /opt/samba-manager/run.py --port 5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    # Create a convenient run script
    echo "Creating run script..."
    cat > /usr/local/bin/samba-manager << EOF
#!/bin/bash
cd /opt/samba-manager
./run_with_sudo.sh
EOF
    chmod +x /usr/local/bin/samba-manager
    
    # Reload systemd, enable and start the service
    echo "Enabling and starting Samba Manager service..."
    systemctl daemon-reload
    systemctl enable samba-manager.service
    systemctl start samba-manager.service
}

# Configure firewall if needed
configure_firewall() {
    echo "Configuring firewall..."
    
    # Ubuntu/Debian with UFW
    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" ]] && command -v ufw &> /dev/null; then
        ufw allow 5000/tcp
        ufw allow Samba
    
    # Fedora/RHEL with firewalld
    elif [[ "$DISTRO" == "fedora" || "$DISTRO" == "rhel" || "$DISTRO" == "centos" ]] && command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=5000/tcp
        firewall-cmd --permanent --add-service=samba
        firewall-cmd --reload
    
    # Arch Linux with iptables
    elif [[ "$DISTRO" == "arch" || "$DISTRO" == "manjaro" ]] && command -v iptables &> /dev/null; then
        # Check if iptables rules exist
        if iptables -L | grep -q "Chain INPUT"; then
            iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
            iptables -A INPUT -p tcp --dport 139 -j ACCEPT
            iptables -A INPUT -p tcp --dport 445 -j ACCEPT
            iptables -A INPUT -p udp --dport 137:138 -j ACCEPT
            
            # Try to save iptables rules if possible
            if command -v iptables-save &> /dev/null; then
                if [[ "$DISTRO" == "arch" ]]; then
                    iptables-save > /etc/iptables/iptables.rules
                else
                    iptables-save > /etc/iptables/rules.v4
                fi
            fi
        fi
    fi
}

# Main installation process
main() {
    install_dependencies
    create_smbusers_group
    install_samba_manager
    create_systemd_service
    configure_firewall
    
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
    echo "Installation directory: /opt/samba-manager"
    echo "=========================================================="
}

# Run the installation
main 