# Terminal Feature Documentation

## Overview

The Samba Manager includes a built-in terminal feature that provides direct command-line access to your server through the web interface. This feature uses GoTTY, a lightweight terminal sharing application that runs in your browser.

## Features

- **Browser-Based Terminal**: Access your server's command line directly from your web browser
- **Full Terminal Emulation**: Complete support for all terminal features and commands
- **Automatic Installation**: Required components (Go and GoTTY) are installed automatically
- **Dynamic Sizing**: Terminal automatically adjusts to fit the browser window
- **Persistent Sessions**: Terminal sessions remain active between page refreshes
- **Secure Access**: Terminal access is integrated with Samba Manager authentication

## Accessing the Terminal

There are two ways to access the terminal:

1. **Dashboard Button**: Click the "Terminal" button in the Quick Actions section of the Dashboard
2. **Sidebar Navigation**: Click the "Terminal" link in the sidebar navigation menu

Both methods will open the terminal in a new browser window or tab.

## Technical Details

### Components

- **GoTTY**: A terminal sharing application that runs in your web browser
- **Go**: The Go programming language runtime required by GoTTY
- **start_terminal_service.sh**: A script that installs and starts the terminal service

### Configuration

The terminal service is configured using a configuration file located at `~/.gotty/config.toml`. The default configuration includes:

```toml
port = 8080
permit_write = true
width = 0
height = 0
title_format = "Terminal - Samba Manager"
enable_resize = true
```

You can modify this file to customize the terminal behavior:

- `port`: The port number for the terminal service (default: 8080)
- `permit_write`: Whether to allow writing to the terminal (default: true)
- `width` and `height`: Terminal dimensions (0 for dynamic sizing)
- `title_format`: The title of the browser window
- `enable_resize`: Whether to allow resizing the terminal

### Starting the Terminal Service

The terminal service starts automatically when you run the Samba Manager application using either:

```bash
./run_app.sh
```

or

```bash
./run_with_sudo.sh
```

You can also start the terminal service manually:

```bash
./start_terminal_service.sh
```

### Port Configuration

By default, the terminal service runs on port 8080. If you need to change this port (for example, if port 8080 is already in use), you can modify the `port` setting in the `~/.gotty/config.toml` file.

If you change the port, you'll also need to update the terminal links in:
- `app/templates/index.html`
- `app/templates/layout.html`

## Security Considerations

The terminal feature provides full command-line access to your server, which comes with significant security implications:

1. **Access Control**: Only users with appropriate permissions should have access to the Samba Manager application
2. **Network Security**: Consider restricting access to port 8080 using a firewall
3. **HTTPS**: For production use, configure a proper HTTPS setup using a reverse proxy
4. **User Permissions**: Be aware that commands run in the terminal will have the same permissions as the user running the Samba Manager application

## Troubleshooting

If you encounter issues with the terminal feature, refer to the [TROUBLESHOOTING.md](TROUBLESHOOTING.md) file for solutions to common problems.

Common issues include:
- Terminal not appearing when clicked
- GoTTY installation problems
- Terminal size issues
- Permission problems

## Advanced Usage

### Custom Terminal Commands

You can modify the `start_terminal_service.sh` script to run a different command instead of the default `bash`. For example, to start a Python interpreter:

```bash
$(go env GOPATH)/bin/gotty -w python &
```

### Multiple Terminal Instances

You can run multiple terminal instances on different ports:

```bash
$(go env GOPATH)/bin/gotty -w -p 8081 bash &
```

Then create additional links pointing to the new port.

### Terminal Customization

GoTTY supports various customization options. For a complete list, run:

```bash
gotty --help
```

Or refer to the [GoTTY documentation](https://github.com/sorenisanerd/gotty). 