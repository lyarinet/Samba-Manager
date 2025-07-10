#!/bin/bash
# Setup script for Samba Manager

echo "Samba Manager Setup Script"
echo "=========================="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root or with sudo"
  exit 1
fi

# Check if Samba is installed
if ! command -v smbd &> /dev/null; then
  echo "Samba is not installed. Installing..."
  apt-get update
  apt-get install -y samba samba-common-bin
else
  echo "Samba is already installed."
fi

# Backup original Samba configuration
echo "Backing up original Samba configuration..."
if [ -f /etc/samba/smb.conf ]; then
  cp /etc/samba/smb.conf /etc/samba/smb.conf.bak.$(date +%Y%m%d%H%M%S)
fi

# Copy configuration files
echo "Copying configuration files..."
cp -f ./smb.conf /etc/samba/smb.conf
cp -f ./shares.conf /etc/samba/shares.conf

# Create shares directory if it doesn't exist
echo "Setting up share directories..."
mkdir -p /var/www/html/files
chmod 777 /var/www/html/files

# Create smbusers group if it doesn't exist
if ! getent group smbusers > /dev/null; then
  echo "Creating smbusers group..."
  groupadd smbusers
fi

# Add current user to smbusers group
echo "Adding current user to smbusers group..."
usermod -aG smbusers $SUDO_USER

# Set permissions for share directories
echo "Setting permissions..."
chown -R $SUDO_USER:smbusers /var/www/html/files
chmod -R 770 /var/www/html/files

# Restart Samba services
echo "Restarting Samba services..."
systemctl restart smbd
systemctl restart nmbd

# Enable Samba services to start on boot
echo "Enabling Samba services to start on boot..."
systemctl enable smbd
systemctl enable nmbd

# Set up Samba user
echo "Setting up Samba user..."
echo "Please enter a password for Samba user $SUDO_USER:"
smbpasswd -a $SUDO_USER

# Display status
echo
echo "Samba services status:"
systemctl status smbd --no-pager
systemctl status nmbd --no-pager

echo
echo "Samba Manager setup complete!"
echo "You can now access your shares at:"
echo "\\\\$(hostname)\\secure-share"
echo "\\\\$(hostname)\\share"
echo "\\\\$(hostname)\\testing"
echo
echo "Make sure your firewall allows Samba traffic (ports 137-139, 445)" 