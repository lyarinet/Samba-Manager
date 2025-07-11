# Samba Manager v1.0.0 Release Notes

## Overview

Samba Manager v1.0.0 is the initial release of a comprehensive web-based interface for managing Samba file sharing on Linux systems. This tool provides an intuitive, user-friendly way to manage Samba configurations, shares, users, and permissions without needing to edit configuration files directly.

## Features

- **Web-Based Administration**: Manage your Samba server through a clean, modern web interface
- **Global Settings Management**: Configure workgroup, server string, security settings, and other global parameters
- **Share Management**:
  - Create, edit, and delete Samba shares with advanced configuration options
  - Set path, permissions, and access controls
  - Configure user and group access restrictions
  - Set connection limits per share
  - Control browseable status and guest access
- **User Management**: Add, modify, and remove Samba users directly from the web interface
- **Group Management**: Create and manage Samba groups for easier permission management
- **Access Control**:
  - User-specific permissions
  - Group-based access control
  - Host allow/deny restrictions
- **Service Control**: Start, stop, restart, and monitor Samba services
- **Log Viewing**: View Samba logs directly from the web interface
- **Import/Export**: Backup and restore your Samba configuration
- **Setup Wizard**: Easy initial configuration for new installations
- **Multi-Mode Operation**:
  - Development mode for testing without system modifications
  - Production mode for actual system configuration management

## Requirements

- Linux system with Samba installed
- Python 3.6+
- Flask and related dependencies
- Sudo access (for modifying system Samba configuration)

## Installation

### Quick Install

1. Download the release package for your system
2. Extract the archive:
   ```bash
   tar -xzf samba-manager-1.0.0.tar.gz
   # or
   unzip samba-manager-1.0.0.zip
   ```
3. Navigate to the extracted directory:
   ```bash
   cd samba-manager-1.0.0
   ```
4. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. Run the application:
   - Development mode (no system changes):
     ```bash
     python run.py --dev
     ```
   - Production mode (modifies system configuration):
     ```bash
     ./run_with_sudo.sh
     ```

### First Login

The default credentials are:
- Username: `admin`
- Password: `admin`

**Important**: Change the default password immediately after first login!

## Known Issues

- No known issues at this time. Please report any issues you encounter.

## Reporting Issues

Please report any issues on the GitHub repository:
https://github.com/lyarinet/samba-manager/issues

## License

This software is released under the MIT License. See the LICENSE file for details.

## Author

Developed by AsifAgaria by Lyarinet. 