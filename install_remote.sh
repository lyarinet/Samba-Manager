#!/bin/bash
#
# Samba Manager Remote Installer
# This script downloads and runs the auto_install.sh script
#

# Check if script is running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root. Please use sudo."
   exit 1
fi

echo "=========================================================="
echo "        Samba Manager Remote Installer"
echo "=========================================================="
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to download the installation script
download_script() {
    local url="https://raw.githubusercontent.com/lyarinet/Samba-Manager/main/auto_install.sh"
    local output="/tmp/samba_manager_auto_install.sh"
    
    echo "Downloading installation script..."
    
    if command_exists curl; then
        curl -sSL "$url" -o "$output"
    elif command_exists wget; then
        wget -q "$url" -O "$output"
    else
        echo "Error: Neither curl nor wget is installed. Please install one of them and try again."
        exit 1
    fi
    
    if [ ! -f "$output" ]; then
        echo "Error: Failed to download the installation script."
        exit 1
    fi
    
    chmod +x "$output"
    echo "Download complete."
    
    return 0
}

# Function to run the installation script
run_script() {
    local script="/tmp/samba_manager_auto_install.sh"
    
    echo "Running installation script..."
    "$script"
    
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Error: Installation failed with exit code $exit_code."
        exit $exit_code
    fi
    
    # Clean up
    rm -f "$script"
    
    return 0
}

# Main function
main() {
    download_script
    run_script
    
    echo ""
    echo "=========================================================="
    echo "        Samba Manager Installation Complete!"
    echo "=========================================================="
}

# Run the main function
main 