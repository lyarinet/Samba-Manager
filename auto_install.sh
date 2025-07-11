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
    
    # Clone the repository (replace with the actual repository URL)
    # For demonstration, we'll use a placeholder URL
    git clone https://github.com/lyarinet/samba_manager.git
    
    if [ $? -ne 0 ]; then
        echo "Failed to download Samba Manager. Please check your internet connection."
        exit 1
    fi
    
    echo "Download complete."
    cd samba_manager
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
    cleanup
    
    echo ""
    echo "=========================================================="
    echo "        Samba Manager Auto-Installation Complete!"
    echo "=========================================================="
    echo "Samba Manager has been successfully installed on your system."
    echo "You can access it at: http://$(hostname -I | awk '{print $1}'):5000"
    echo "=========================================================="
}

# Run the main function
main 