#!/bin/bash
# Setup script for Samba Manager with enhanced user management

echo "Samba Manager Setup Script"
echo "=========================="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root or with sudo"
  exit 1
fi

# Function to add a Samba user
add_samba_user() {
  local username="$1"
  local password="$2"
  
  # Check if system user exists
  if ! id "$username" &>/dev/null; then
    echo "Creating system user: $username"
    useradd -m -s /bin/bash "$username"
    echo "$username:$password" | chpasswd
  fi
  
  # Add to smbusers group
  usermod -aG smbusers "$username"
  
  # Add Samba user
  echo "Adding Samba user: $username"
  (echo "$password"; echo "$password") | smbpasswd -s -a "$username"
  
  # Enable the Samba user
  smbpasswd -e "$username"
  
  echo "User $username has been added to Samba"
}

# Function to list all Samba users
list_samba_users() {
  echo "Current Samba users:"
  pdbedit -L | cut -d: -f1
}

# Function to configure global Samba settings
configure_global_settings() {
  local workgroup="$1"
  local server_string="$2"
  local log_level="$3"
  
  cat > /etc/samba/smb.conf << EOF
[global]
   workgroup = $workgroup
   server string = $server_string
   log level = $log_level
   security = user
   passdb backend = tdbsam
   map to guest = bad user
   dns proxy = no
   usershare allow guests = yes
   include = /etc/samba/shares.conf

[printers]
   comment = All Printers
   browseable = no
   path = /var/tmp
   printable = yes
   guest ok = no
   read only = yes
   create mask = 0700

[print$]
   comment = Printer Drivers
   path = /var/lib/samba/printers
   browseable = yes
   read only = yes
   guest ok = no
EOF

  echo "Global Samba settings configured"
}

# Function to create a share
create_share() {
  local name="$1"
  local path="$2"
  local valid_users="$3"
  local read_only="$4"
  local guest_ok="$5"
  local comment="$6"
  
  # Create directory if it doesn't exist
  mkdir -p "$path"
  
  # Add share to shares.conf
  cat >> /etc/samba/shares.conf << EOF

[$name]
   comment = $comment
   path = $path
   valid users = $valid_users
   read only = $read_only
   guest ok = $guest_ok
   browseable = yes
   create mask = 0770
   directory mask = 0770
   force group = smbusers
   force user = root
EOF

  # Set permissions
  chown -R root:smbusers "$path"
  chmod -R 2770 "$path"  # 2 sets the SGID bit
  
  echo "Share '$name' created at '$path'"
}

# Function to check if user is already a Samba user
is_samba_user() {
  local username="$1"
  pdbedit -L | grep -q "^$username:"
  return $?
}

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

# Initialize shares.conf
echo "# Samba shares configuration" > /etc/samba/shares.conf

# Configure global settings
echo "Configuring global Samba settings..."
configure_global_settings "WORKGROUP" "Samba Server" "1"

# Create default shares
echo "Creating default shares..."
create_share "public" "/srv/samba/public" "@smbusers" "no" "yes" "Public Share"
create_share "secure-share" "/var/www" "@smbusers,root" "no" "no" "Secure Shared Folder with Full Access"
create_share "share" "/home/fida/samba_manager" "@smbusers,root" "no" "no" "Samba Manager Share"
create_share "testing" "/var/www/html/files" "@smbusers" "no" "no" "Testing Share"

# Add current user to Samba
echo "Setting up Samba users..."

# First, check for existing Samba users
echo "Checking for existing Samba users..."
EXISTING_USERS=$(pdbedit -L | cut -d: -f1)
if [ -n "$EXISTING_USERS" ]; then
  echo "Found existing Samba users:"
  echo "$EXISTING_USERS"
  echo "These users will be preserved."
fi

if [ -n "$SUDO_USER" ]; then
  # Check if current user is already a Samba user
  if is_samba_user "$SUDO_USER"; then
    echo "User $SUDO_USER is already a Samba user"
  else
    # Interactive mode
    echo "Please enter password for Samba user $SUDO_USER:"
    read -s user_password
    echo
    
    add_samba_user "$SUDO_USER" "$user_password"
  fi
  
  # Ask if user wants to add more users
  while true; do
    echo
    echo "Do you want to add another Samba user? (y/n)"
    read -r answer
    if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
      break
    fi
    
    echo "Enter username:"
    read -r new_username
    
    # Check if user is already a Samba user
    if is_samba_user "$new_username"; then
      echo "User $new_username is already a Samba user"
      continue
    fi
    
    echo "Enter password for $new_username:"
    read -s new_password
    echo
    
    add_samba_user "$new_username" "$new_password"
  done
else
  echo "Warning: SUDO_USER not set. Cannot determine current user."
  echo "Please add Samba users manually using:"
  echo "  sudo smbpasswd -a username"
fi

# Restart Samba services
echo "Restarting Samba services..."
systemctl restart smbd
systemctl restart nmbd

# Enable Samba services to start on boot
echo "Enabling Samba services to start on boot..."
systemctl enable smbd
systemctl enable nmbd

# List all configured users
echo
list_samba_users

# Display status
echo
echo "Samba services status:"
systemctl status smbd --no-pager
systemctl status nmbd --no-pager

echo
echo "Samba Manager setup complete!"
echo "You can now access your shares at:"
echo "\\\\$(hostname)\\public"
echo "\\\\$(hostname)\\secure-share"
echo "\\\\$(hostname)\\share"
echo "\\\\$(hostname)\\testing"
echo
echo "Make sure your firewall allows Samba traffic (ports 137-139, 445)"

# Create a helper script for managing users later
cat > manage_samba_users.sh << 'EOF'
#!/bin/bash
# Samba user management script

if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root or with sudo"
  exit 1
fi

show_menu() {
  clear
  echo "========================================="
  echo "       Samba User Management Tool        "
  echo "========================================="
  echo "1. List all Samba users"
  echo "2. Add a new Samba user"
  echo "3. Delete a Samba user"
  echo "4. Reset a Samba user password"
  echo "5. Enable a Samba user"
  echo "6. Disable a Samba user"
  echo "7. Exit"
  echo "========================================="
  echo "Enter your choice [1-7]: "
}

list_users() {
  echo "Current Samba users:"
  pdbedit -L -v | grep -E "Unix username|Account Flags"
  echo
  read -p "Press Enter to continue..."
}

add_user() {
  echo "Enter the username to add:"
  read -r username
  
  # Check if system user exists
  if ! id "$username" &>/dev/null; then
    echo "System user does not exist. Create it? (y/n)"
    read -r create_user
    if [[ "$create_user" == "y" || "$create_user" == "Y" ]]; then
      useradd -m -s /bin/bash "$username"
      echo "Enter system password for $username:"
      passwd "$username"
    else
      echo "Cannot add Samba user without system user"
      return
    fi
  fi
  
  # Add to smbusers group
  usermod -aG smbusers "$username"
  
  # Add Samba user
  echo "Enter Samba password for $username:"
  smbpasswd -a "$username"
  
  echo "User $username has been added to Samba"
  read -p "Press Enter to continue..."
}

delete_user() {
  echo "Current Samba users:"
  pdbedit -L | cut -d: -f1
  echo
  echo "Enter the username to delete:"
  read -r username
  
  echo "WARNING: This will remove the user from Samba."
  echo "Do you also want to remove the system user? (y/n)"
  read -r remove_system
  
  # Delete Samba user
  smbpasswd -x "$username"
  
  if [[ "$remove_system" == "y" || "$remove_system" == "Y" ]]; then
    userdel -r "$username"
    echo "System user $username has been removed"
  fi
  
  echo "Samba user $username has been removed"
  read -p "Press Enter to continue..."
}

reset_password() {
  echo "Current Samba users:"
  pdbedit -L | cut -d: -f1
  echo
  echo "Enter the username to reset password:"
  read -r username
  
  # Reset Samba password
  smbpasswd "$username"
  
  echo "Password for $username has been reset"
  read -p "Press Enter to continue..."
}

enable_user() {
  echo "Disabled Samba users:"
  pdbedit -L -v | grep -B 1 "[D" | grep "Unix username" | awk '{print $3}'
  echo
  echo "Enter the username to enable:"
  read -r username
  
  # Enable Samba user
  smbpasswd -e "$username"
  
  echo "User $username has been enabled"
  read -p "Press Enter to continue..."
}

disable_user() {
  echo "Current Samba users:"
  pdbedit -L | cut -d: -f1
  echo
  echo "Enter the username to disable:"
  read -r username
  
  # Disable Samba user
  smbpasswd -d "$username"
  
  echo "User $username has been disabled"
  read -p "Press Enter to continue..."
}

# Main loop
while true; do
  show_menu
  read -r choice
  
  case $choice in
    1) list_users ;;
    2) add_user ;;
    3) delete_user ;;
    4) reset_password ;;
    5) enable_user ;;
    6) disable_user ;;
    7) echo "Exiting..."; exit 0 ;;
    *) echo "Invalid option. Press Enter to continue..."; read ;;
  esac
done
EOF

chmod +x manage_samba_users.sh
echo "Created user management script: manage_samba_users.sh"
echo "Run 'sudo ./manage_samba_users.sh' to manage Samba users"

# Fix permissions on existing share directories
echo "Fixing permissions on existing share directories..."
if [ -d "/var/www" ]; then
  echo "Setting permissions for /var/www..."
  chown -R root:smbusers /var/www
  chmod -R 2770 /var/www
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