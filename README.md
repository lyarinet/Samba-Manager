# Samba Manager

A web-based interface for managing Samba shares and configuration.

## Features

- Manage Samba global settings
- Create, update, and delete shares
- Monitor Samba service status
- Export and import configurations
- User and group integration
- View both system and local shares

## Requirements

- Python 3.6+
- Samba
- Sudo access (for modifying Samba configuration)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/samba_manager.git
   cd samba_manager
   ```

2. Create a virtual environment and install dependencies:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Setting Up Samba

For the Samba Manager to work properly, you need to have Samba installed and configured correctly. We've provided a setup script to help you with this:

1. Make the setup script executable:
   ```
   chmod +x setup_samba.sh
   ```

2. Run the setup script as root:
   ```
   sudo ./setup_samba.sh
   ```

This script will:
- Install Samba if it's not already installed
- Configure the shares properly
- Set up the required permissions
- Create and configure a Samba user
- Restart the Samba services

## Running the Application

### Development Mode

In development mode, the application uses local configuration files and doesn't require sudo privileges:

```
source venv/bin/activate
python run.py
```

The web interface will be available at http://localhost:5000

### Production Mode

For production use, you should set `DEV_MODE = False` in `app/samba_utils.py` and run with sudo:

```
sudo /path/to/venv/bin/python run.py
```

## Accessing Shares

After setting up Samba and creating shares, you can access them from:

### Windows

1. Open File Explorer
2. In the address bar, type: `\\your-server-ip\sharename`
3. Enter your Samba username and password when prompted

### Linux

1. Open your file manager
2. Connect to server: `smb://your-server-ip/sharename`
3. Enter your Samba username and password when prompted

### macOS

1. In Finder, press Cmd+K
2. Enter: `smb://your-server-ip/sharename`
3. Enter your Samba username and password when prompted

## Troubleshooting

If you encounter issues with your Samba shares, please refer to the [Troubleshooting Guide](TROUBLESHOOTING.md).

## Security Considerations

- This application requires sudo access to modify Samba configuration files and restart services
- In production environments, consider using a more secure approach like sudo rules or a dedicated service user
- The application uses a random secret key by default - for production, set a consistent SECRET_KEY environment variable

## License

MIT
