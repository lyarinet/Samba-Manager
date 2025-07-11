# Samba Manager Troubleshooting Guide

## Common Issues and Solutions

### Shares Not Showing Up in File Explorer

1. **Check if Samba is installed and running:**
   ```bash
   sudo systemctl status smbd
   sudo systemctl status nmbd
   ```
   If not running, start the services:
   ```bash
   sudo systemctl start smbd
   sudo systemctl start nmbd
   ```

2. **Check if your firewall is blocking Samba:**
   ```bash
   sudo ufw status
   ```
   If the firewall is active, allow Samba traffic:
   ```bash
   sudo ufw allow samba
   ```

3. **Verify Samba user exists:**
   ```bash
   sudo pdbedit -L
   ```
   If your user is not listed, add it:
   ```bash
   sudo smbpasswd -a yourusername
   ```

4. **Check share permissions:**
   ```bash
   ls -la /path/to/share
   ```
   Make sure the directory has appropriate permissions (e.g., 770) and is owned by the correct user/group.

5. **Test Samba configuration:**
   ```bash
   testparm
   ```
   This will check your smb.conf for errors.

6. **Restart Samba after configuration changes:**
   ```bash
   sudo systemctl restart smbd
   sudo systemctl restart nmbd
   ```

7. **Check network connectivity:**
   Make sure your computer can connect to the Samba server:
   ```bash
   ping hostname-or-ip
   ```

### Terminal Feature Issues

1. **Terminal not appearing when clicked:**
   - Check if GoTTY is installed and running:
     ```bash
     ps aux | grep gotty
     ```
   - If not running, start it manually:
     ```bash
     ./start_terminal_service.sh
     ```
   - Verify port 8080 is available:
     ```bash
     sudo netstat -tuln | grep 8080
     ```

2. **GoTTY installation issues:**
   - Verify Go is installed:
     ```bash
     go version
     ```
   - If Go is not installed:
     ```bash
     sudo apt update
     sudo apt install -y golang-go
     ```
   - Install GoTTY manually:
     ```bash
     go install github.com/sorenisanerd/gotty@latest
     export PATH=$PATH:$(go env GOPATH)/bin
     ```

3. **Terminal size issues:**
   - Check GoTTY configuration:
     ```bash
     cat ~/.gotty/config.toml
     ```
   - Make sure width and height are set to 0 for dynamic sizing:
     ```
     width = 0
     height = 0
     ```

4. **Terminal access permissions:**
   - Make sure the user running GoTTY has appropriate permissions
   - For sudo access in the terminal, make sure the user has sudo privileges

5. **Browser issues:**
   - Try a different browser (Chrome or Firefox recommended)
   - Clear browser cache and cookies
   - Check browser console for JavaScript errors

### Access Denied Errors

1. **Check if the Samba user has the correct password:**
   Reset the Samba password:
   ```bash
   sudo smbpasswd -a yourusername
   ```

2. **Verify user is in the correct group:**
   ```bash
   groups yourusername
   ```
   Add user to the smbusers group if needed:
   ```bash
   sudo usermod -aG smbusers yourusername
   ```

3. **Check share configuration:**
   Make sure the `valid users` parameter includes your username or group.

### Permission Issues

1. **Fix directory permissions:**
   ```bash
   sudo chown -R yourusername:smbusers /path/to/share
   sudo chmod -R 770 /path/to/share
   ```

2. **Check SELinux (if applicable):**
   ```bash
   sudo sestatus
   ```
   If SELinux is enforcing, set the correct context:
   ```bash
   sudo chcon -R -t samba_share_t /path/to/share
   ```

## Windows-Specific Issues

1. **Shares not visible in Network:**
   - Make sure Network Discovery is turned on
   - Check if the Windows Firewall is blocking access
   - Try accessing the share directly using the UNC path: `\\server-ip\sharename`

2. **Cannot connect to shares:**
   - Make sure the Windows user has the same username/password as the Samba user
   - Try connecting with explicit credentials: `net use Z: \\server-ip\sharename /user:username password`

3. **Reset Windows SMB cache:**
   ```
   net use * /delete
   ```

## Run the Setup Script

If you're still having issues, run the setup script as root:

```bash
sudo ./setup_samba.sh
```

This script will:
- Install Samba if it's not already installed
- Configure the shares properly
- Set up the required permissions
- Create and configure a Samba user
- Restart the Samba services

## Manual Configuration Check

You can manually verify your Samba configuration:

1. Check `/etc/samba/smb.conf` for proper global settings
2. Check `/etc/samba/shares.conf` for proper share definitions
3. Verify that the `include = /etc/samba/shares.conf` line exists in the global section of smb.conf

## Getting More Help

If you're still having issues, check the Samba logs:

```bash
sudo tail -f /var/log/samba/log.smbd
```

You can also get more detailed logs by increasing the log level in the global section of smb.conf:
```
log level = 3
``` 