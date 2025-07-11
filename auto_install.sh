#!/bin/bash
#
# Samba Manager Auto-Installation Script
# This script downloads and installs Samba Manager on any Linux distribution
#

# Check if script is running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root. Please use sudo."
   exit 1
fi

echo "=========================================================="
echo "        Samba Manager Auto-Installation Script"
echo "=========================================================="
echo ""

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
echo "Created temporary directory: $TEMP_DIR"
cd $TEMP_DIR

# Check for required tools
check_requirements() {
    echo "Checking for required tools..."
    
    # Check for git
    if ! command -v git &> /dev/null; then
        echo "Git is not installed. Installing..."
        
        # Detect the Linux distribution
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO=$ID
            DISTRO_FAMILY=$ID_LIKE
        else
            echo "Cannot detect Linux distribution. Please install git manually."
            exit 1
        fi
        
        # Install git based on distribution
        if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" || "$DISTRO_FAMILY" == *"debian"* ]]; then
            apt-get update
            apt-get install -y git
        elif [[ "$DISTRO" == "fedora" || "$DISTRO" == "rhel" || "$DISTRO" == "centos" || "$DISTRO_FAMILY" == *"fedora"* || "$DISTRO_FAMILY" == *"rhel"* ]]; then
            dnf install -y git
        elif [[ "$DISTRO" == "arch" || "$DISTRO" == "manjaro" || "$DISTRO_FAMILY" == *"arch"* ]]; then
            pacman -Sy --noconfirm git
        else
            echo "Unsupported distribution for automatic git installation."
            echo "Please install git manually and run this script again."
            exit 1
        fi
    fi
    
    echo "Git is installed."
}

# Download Samba Manager
download_samba_manager() {
    echo "Downloading Samba Manager from repository..."
    
    # Clone the repository with the correct URL
    git clone https://github.com/lyarinet/Samba-Manager.git
    
    if [ $? -ne 0 ]; then
        echo "Failed to download Samba Manager. Please check your internet connection."
        exit 1
    fi
    
    echo "Download complete."
    cd Samba-Manager
}

# Run the installation script
run_installation() {
    echo "Running installation script..."
    
    # Make the installation script executable
    chmod +x install_all_distros.sh
    
    # Run the installation script
    ./install_all_distros.sh
    
    if [ $? -ne 0 ]; then
        echo "Installation failed. Please check the error messages above."
        exit 1
    fi
}

# Configure network access
configure_network_access() {
    echo "Configuring network access for remote connections..."
    
    # Make the fix script executable
    chmod +x fix_network_access.sh
    
    # Run the network access fix script
    ./fix_network_access.sh
    
    if [ $? -ne 0 ]; then
        echo "Warning: Network access configuration may not be complete."
        echo "You may need to run 'sudo /opt/samba-manager/fix_network_access.sh' manually."
    else
        echo "Network access configured successfully."
    fi
}

# Clean up
cleanup() {
    echo "Cleaning up temporary files..."
    cd /
    rm -rf $TEMP_DIR
    echo "Cleanup complete."
}

# Main function
main() {
    check_requirements
    download_samba_manager
    run_installation
    configure_network_access
    cleanup
    
    echo ""
    echo "=========================================================="
    echo "        Samba Manager Auto-Installation Complete!"
    echo "=========================================================="
    echo "Samba Manager has been successfully installed on your system."
    echo "You can access it at: http://$(hostname -I | awk '{print $1}'):5000"
    echo "Terminal service is available at: http://$(hostname -I | awk '{print $1}'):8080"
    echo ""
    echo "Both services should be accessible from other computers on your network."
    echo "If you have connection issues, run: sudo /opt/samba-manager/fix_network_access.sh"
    echo "=========================================================="
}

# Run the main function
main 