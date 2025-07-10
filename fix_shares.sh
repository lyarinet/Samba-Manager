#!/bin/bash
# Quick fix script for Samba Manager

echo "Samba Manager Quick Fix Script"
echo "============================="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root or with sudo"
  exit 1
fi

# Create smbusers group if it doesn't exist
if ! getent group smbusers > /dev/null; then
  echo "Creating smbusers group..."
  groupadd smbusers
fi

# Add all existing users to smbusers group
echo "Adding existing users to smbusers group..."
for user in $(getent passwd | awk -F: '$3 >= 1000 && $3 < 65534 {print $1}'); do
  if id -u "$user" >/dev/null 2>&1; then
    echo "Adding user $user to smbusers group"
    usermod -aG smbusers "$user"
  fi
done

# Fix permissions on existing share directories
echo "Fixing permissions on existing share directories..."
if [ -d "/var/www" ]; then
  echo "Setting permissions for /var/www..."
  chown -R root:smbusers /var/www
  chmod -R 2770 /var/www
fi

if [ -d "/var/www/html" ]; then
  echo "Setting permissions for /var/www/html..."
  chown -R root:smbusers /var/www/html
  chmod -R 2770 /var/www/html
fi

if [ -d "/var/www/html/files" ]; then
  echo "Setting permissions for /var/www/html/files..."
  chown -R root:smbusers /var/www/html/files
  chmod -R 2770 /var/www/html/files
fi

if [ -d "/srv/samba/public" ]; then
  echo "Setting permissions for /srv/samba/public..."
  chown -R root:smbusers /srv/samba/public
  chmod -R 2770 /srv/samba/public
fi

if [ -d "/home/fida/samba_manager" ]; then
  echo "Setting permissions for /home/fida/samba_manager..."
  chown -R root:smbusers /home/fida/samba_manager
  chmod -R 2770 /home/fida/samba_manager
fi

# Create missing directories
echo "Creating missing share directories..."
mkdir -p /var/www/html/files
chown -R root:smbusers /var/www/html/files
chmod -R 2770 /var/www/html/files

mkdir -p /srv/samba/public
chown -R root:smbusers /srv/samba/public
chmod -R 2770 /srv/samba/public

# Check if Samba is installed
if ! command -v smbd &>/dev/null; then
  echo "Samba is not installed. Installing..."
  apt-get update
  apt-get install -y samba samba-common-bin
else
  echo "Samba is already installed."
fi

# Restart Samba services
echo "Restarting Samba services..."
systemctl restart smbd
systemctl restart nmbd

# Enable Samba services to start on boot
echo "Enabling Samba services to start on boot..."
systemctl enable smbd
systemctl enable nmbd

# Display Samba users
echo
echo "Current Samba users:"
pdbedit -L | cut -d: -f1

echo
echo "Quick fix completed!"
echo "You can now access your shares at:"
echo "\\\\$(hostname)\\secure-share"
echo "\\\\$(hostname)\\share"
echo "\\\\$(hostname)\\testing"
echo
echo "If you still have issues, run the full setup script: sudo ./setup_samba.sh" 