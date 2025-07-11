#!/bin/bash
#
# Samba Manager Installation Script with GitHub Authentication
# This script downloads and installs Samba Manager from a GitHub repository
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

# Ask for GitHub credentials if needed
read -p "Do you need to authenticate with GitHub? (y/n): " need_auth
if [[ "$need_auth" == "y" || "$need_auth" == "Y" ]]; then
    read -p "Enter GitHub username: " github_username
    read -s -p "Enter GitHub password or personal access token: " github_token
    echo ""
    
    # Create temporary netrc file for authentication
    cat > ~/.netrc << EOF
machine github.com
login $github_username
password $github_token
machine api.github.com
login $github_username
password $github_token
EOF
    
    chmod 600 ~/.netrc
    echo "GitHub authentication configured."
fi

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
    
    # Try to clone the repository
    echo "Attempting to clone from: https://github.com/lyarinet/Samba-Manager.git"
    git clone https://github.com/lyarinet/Samba-Manager.git
    
    # If that fails, try with the lowercase name
    if [ $? -ne 0 ]; then
        echo "First attempt failed. Trying alternate repository name..."
        git clone https://github.com/lyarinet/samba_manager.git
        
        if [ $? -ne 0 ]; then
            echo "Failed to download Samba Manager."
            echo "Please check your internet connection and GitHub credentials."
            
            # Ask for repository URL
            read -p "Enter the correct repository URL (e.g., https://github.com/username/repo.git): " repo_url
            git clone "$repo_url"
            
            if [ $? -ne 0 ]; then
                echo "Failed to clone repository. Exiting."
                exit 1
            fi
            
            # Get the directory name from the repo URL
            REPO_DIR=$(basename "$repo_url" .git)
            cd "$REPO_DIR"
        else
            echo "Download complete using alternate name."
            cd samba_manager
        fi
    else
        echo "Download complete."
        cd Samba-Manager
    fi
}

# Run the installation script
run_installation() {
    echo "Running installation script..."
    
    # Check which installation script exists
    if [ -f "install_all_distros.sh" ]; then
        chmod +x install_all_distros.sh
        ./install_all_distros.sh
    elif [ -f "install.sh" ]; then
        chmod +x install.sh
        ./install.sh
    else
        echo "No installation script found. Available files:"
        ls -la
        exit 1
    fi
    
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
    
    # Remove netrc file if it was created
    if [[ "$need_auth" == "y" || "$need_auth" == "Y" ]]; then
        rm -f ~/.netrc
    fi
    
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
    echo "        Samba Manager Installation Complete!"
    echo "=========================================================="
    echo "Samba Manager has been successfully installed on your system."
    echo "You can access it at: http://$(hostname -I | awk '{print $1}'):5000"
    echo "=========================================================="
}

# Run the main function
main 