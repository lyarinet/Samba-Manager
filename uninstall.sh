#!/bin/bash
#
# Samba Manager Uninstall Script
#

# Check if script is running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root. Please use sudo."
   exit 1
fi

echo "=========================================================="
echo "        Samba Manager Uninstall Script"
echo "=========================================================="
echo ""

# Function to confirm uninstallation
confirm_uninstall() {
    echo "WARNING: This will completely remove Samba Manager from your system."
    echo "This includes:"
    echo "  - All Samba Manager files in /opt/samba-manager"
    echo "  - The samba-manager systemd service"
    echo "  - The samba-manager command"
    echo ""
    echo "Note: Your Samba configuration files and shares will NOT be removed."
    echo "      Only the Samba Manager web interface will be uninstalled."
    echo ""
    
    read -p "Are you sure you want to uninstall Samba Manager? (y/n): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Uninstallation cancelled."
        exit 0
    fi
    
    echo ""
    echo "Proceeding with uninstallation..."
    echo ""
}

# Function to stop and disable the service
stop_service() {
    echo "Stopping and disabling Samba Manager service..."
    
    # Check if the service exists
    if systemctl list-unit-files | grep -q samba-manager.service; then
        systemctl stop samba-manager.service
        systemctl disable samba-manager.service
        echo "Service stopped and disabled."
    else
        echo "Service not found, skipping."
    fi
}

# Function to remove the service file
remove_service_file() {
    echo "Removing systemd service file..."
    
    if [ -f /etc/systemd/system/samba-manager.service ]; then
        rm -f /etc/systemd/system/samba-manager.service
        systemctl daemon-reload
        echo "Service file removed."
    else
        echo "Service file not found, skipping."
    fi
}

# Function to remove the command symlink
remove_command() {
    echo "Removing samba-manager commands..."
    
    if [ -f /usr/local/bin/samba-manager ]; then
        rm -f /usr/local/bin/samba-manager
        echo "Command 'samba-manager' removed."
    else
        echo "Command 'samba-manager' not found, skipping."
    fi
    
    if [ -f /usr/local/bin/samba-manager-uninstall ]; then
        rm -f /usr/local/bin/samba-manager-uninstall
        echo "Command 'samba-manager-uninstall' removed."
    else
        echo "Command 'samba-manager-uninstall' not found, skipping."
    fi
}

# Function to remove installation directory
remove_files() {
    echo "Removing Samba Manager files..."
    
    if [ -d /opt/samba-manager ]; then
        rm -rf /opt/samba-manager
        echo "Files removed."
    else
        echo "Installation directory not found, skipping."
    fi
}

# Function to kill any running terminal sessions
kill_terminal_sessions() {
    echo "Terminating any active terminal sessions..."
    
    # Kill any GoTTY processes
    if pgrep -f "gotty -w" > /dev/null; then
        pkill -f "gotty -w"
        echo "Terminal sessions terminated."
    else
        echo "No active terminal sessions found."
    fi
}

# Function to check if Samba was installed by the script
check_samba_installation() {
    echo "Checking Samba installation..."
    
    if command -v smbd &> /dev/null; then
        echo ""
        echo "Samba is still installed on your system."
        echo "If you want to remove Samba as well, you can use your package manager:"
        echo ""
        
        # Detect the Linux distribution
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO=$ID
            DISTRO_FAMILY=$ID_LIKE
            
            if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" || "$DISTRO_FAMILY" == *"debian"* ]]; then
                echo "  sudo apt remove samba samba-common smbclient"
            elif [[ "$DISTRO" == "fedora" || "$DISTRO" == "rhel" || "$DISTRO" == "centos" || "$DISTRO_FAMILY" == *"fedora"* || "$DISTRO_FAMILY" == *"rhel"* ]]; then
                echo "  sudo dnf remove samba samba-client"
            elif [[ "$DISTRO" == "arch" || "$DISTRO" == "manjaro" || "$DISTRO_FAMILY" == *"arch"* ]]; then
                echo "  sudo pacman -R samba"
            else
                echo "  Please use your distribution's package manager to remove Samba"
            fi
        fi
        
        echo ""
        echo "Note: Removing Samba will also remove your Samba configuration and shares."
    else
        echo "Samba is not installed or not found in PATH."
    fi
}

# Main uninstall function
uninstall() {
    confirm_uninstall
    kill_terminal_sessions
    stop_service
    remove_service_file
    remove_command
    remove_files
    check_samba_installation
    
    echo ""
    echo "=========================================================="
    echo "        Samba Manager Uninstallation Complete"
    echo "=========================================================="
    echo ""
    echo "Samba Manager has been successfully uninstalled from your system."
    echo "Thank you for using Samba Manager!"
    echo "=========================================================="
}

# Run the uninstall function
uninstall 