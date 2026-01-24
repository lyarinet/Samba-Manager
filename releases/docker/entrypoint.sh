#!/bin/bash
# Docker entrypoint for Samba Manager

set -e

echo "Starting Samba Manager..."
echo "=========================="
echo ""

# Environment variables
export SAMBA_MANAGER_SECRET_KEY="${SAMBA_MANAGER_SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_hex(32))')}"
export FLASK_ENV="${FLASK_ENV:-production}"

# Initialize Samba configuration if not present
if [ ! -f /etc/samba/smb.conf ]; then
    echo "Initializing Samba configuration..."
    if [ -f /opt/samba-manager/smb.conf.template ]; then
        cp /opt/samba-manager/smb.conf.template /etc/samba/smb.conf
        echo "✓ Samba configuration initialized from template"
    fi
fi

# Create shares.d directory if it doesn't exist
mkdir -p /etc/samba/shares.d
echo "✓ Samba shares directory ready"

# Set proper permissions
chmod 755 /etc/samba
chmod 644 /etc/samba/smb.conf 2>/dev/null || true
chmod 755 /etc/samba/shares.d

# Create log directories if they don't exist
mkdir -p /var/log/samba-manager
mkdir -p /var/log/samba
chmod 755 /var/log/samba-manager
chmod 755 /var/log/samba

echo "✓ Directories initialized"
echo "✓ Environment configured"
echo ""
echo "Starting services..."
echo "- Samba Manager on port 5000"
echo "- Samba daemon (smbd)"
echo ""

# Start the supervisord daemon
exec "$@"
