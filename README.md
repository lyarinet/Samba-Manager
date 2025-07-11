# Samba Manager

A comprehensive web-based interface for managing Samba file sharing on Linux systems.

![Samba Manager](https://github.com/user-attachments/assets/61670b6f-0d9b-445e-a74e-c57c58342c54)

## Features

- **Web-Based Administration**: Manage your Samba server through an intuitive web interface
- **Global Settings Management**: Configure workgroup, server string, security settings, and other global parameters
- **Share Management**: Create, edit, and delete Samba shares with advanced configuration options
  - Set path, permissions, and access controls
  - Configure user and group access restrictions
  - Set connection limits per share
  - Control browseable status and guest access
- **User Management**: Add, modify, and remove Samba users directly from the web interface
- **Group Management**: Create and manage Samba groups for easier permission management
- **Access Control**: Fine-grained control over who can access shares
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

### 1. Clone the Repository

```bash
git clone https://github.com/lyarinet/samba-manager.git
cd samba-manager
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run in Development Mode (Optional)

This mode uses local configuration files instead of system files, great for testing:

```bash
python run.py --dev
```

### 5. Run in Production Mode

For actual system configuration management:

```bash
./run_with_sudo.sh
```

The web interface will be accessible at http://your-server-ip:5000

## Setup

1. **First Login**: The default credentials are username: `admin`, password: `admin` (change immediately after first login)
2. **Global Settings**: Configure your workgroup, security settings, and other global parameters
3. **Add Users**: Create Samba users that will access your shares
4. **Create Shares**: Set up the directories you want to share
5. **Configure Permissions**: Set appropriate permissions for each share
6. **Restart Service**: Apply changes by restarting the Samba service

## Security Considerations

- **Change Default Password**: Immediately change the default admin password
- **Network Security**: Restrict access to the web interface using a firewall
- **Sudo Access**: The application requires sudo access to modify system configuration files
- **Custom Sudo Rules**: Consider setting up specific sudo rules for production environments
- **HTTPS**: For production use, configure a proper HTTPS setup using a reverse proxy

## Troubleshooting

If you encounter issues:

1. **Check Logs**: Review logs in the Maintenance section
2. **Verify Permissions**: Ensure proper file system permissions on shared directories
3. **Service Status**: Confirm Samba services are running
4. **Network Access**: Verify network connectivity and firewall settings
5. **See the Troubleshooting Guide**: Refer to [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

## Advanced Configuration

- **Custom Samba Configuration**: Edit the Samba configuration directly in the advanced mode
- **Host Restrictions**: Limit access to shares by IP address or network
- **Connection Limits**: Set maximum number of connections per share
- **User Management**: Create specific users for Samba access

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Author

Developed by AsifAgaria by Lyarinet.

---

## Screenshots

![Dashboard](https://github.com/user-attachments/assets/61670b6f-0d9b-445e-a74e-c57c58342c54)
![Shares Management](https://via.placeholder.com/400x200?text=Shares+Management)
![Global Settings](https://via.placeholder.com/400x200?text=Global+Settings)
