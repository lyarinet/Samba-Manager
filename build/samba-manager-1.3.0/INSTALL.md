# Samba Manager Installation Guide

This document provides instructions for installing Samba Manager on various Linux distributions.

## Automatic Installation (Recommended)

The easiest way to install Samba Manager is to use our automatic installation script, which works on Ubuntu, Debian, Fedora, RHEL, CentOS, Arch Linux, and Manjaro.

### One-line Installation

```bash
curl -sSL https://raw.githubusercontent.com/lyarinet/Samba-Manager/main/auto_install.sh | sudo bash
```

Or if you prefer wget:

```bash
wget -qO- https://raw.githubusercontent.com/lyarinet/Samba-Manager/main/auto_install.sh | sudo bash
```

### Manual Download and Install

If you prefer to review the script before running it:

1. Download the auto-installation script:
   ```bash
   wget https://raw.githubusercontent.com/lyarinet/Samba-Manager/main/auto_install.sh
   ```

2. Make it executable:
   ```bash
   chmod +x auto_install.sh
   ```

3. Run the script with sudo:
   ```bash
   sudo ./auto_install.sh
   ```

## Distribution-specific Manual Installation

If you prefer to install manually or if the automatic installation fails, you can follow these distribution-specific instructions:

### Ubuntu/Debian

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3-venv samba samba-common smbclient

# Clone the repository
git clone https://github.com/lyarinet/Samba-Manager.git
cd Samba-Manager

# Run the installation script
sudo ./install.sh
```

### Fedora/RHEL/CentOS

```bash
# Install dependencies
sudo dnf update -y
sudo dnf install -y git python3 python3-pip samba samba-client

# Clone the repository
git clone https://github.com/lyarinet/Samba-Manager.git
cd Samba-Manager

# Run the installation script
sudo ./install_all_distros.sh
```

### Arch Linux/Manjaro

```bash
# Install dependencies
sudo pacman -Syu --noconfirm
sudo pacman -S --noconfirm git python python-pip samba

# Clone the repository
git clone https://github.com/lyarinet/Samba-Manager.git
cd Samba-Manager

# Run the installation script
sudo ./install_all_distros.sh
```

## Post-Installation

After installation, Samba Manager will be:

1. Installed at `/opt/samba-manager`
2. Running as a systemd service
3. Accessible via web browser at `http://your-server-ip:5000`

### Default Login Credentials

- Username: `admin`
- Password: `admin`

**IMPORTANT:** Change the default password after your first login!

### Managing the Service

```bash
# Start the service
sudo systemctl start samba-manager.service

# Stop the service
sudo systemctl stop samba-manager.service

# Restart the service
sudo systemctl restart samba-manager.service

# Check the service status
sudo systemctl status samba-manager.service
```

### Running Manually

You can also run Samba Manager manually using:

```bash
sudo samba-manager
```

## Troubleshooting

If you encounter any issues during installation, please:

1. Check that your system meets the minimum requirements
2. Ensure you have a stable internet connection
3. Verify that you have sufficient permissions (running with sudo)
4. Check the logs in `/opt/samba-manager/logs/`

For additional help, please refer to the [TROUBLESHOOTING.md](TROUBLESHOOTING.md) file or open an issue on our GitHub repository. 