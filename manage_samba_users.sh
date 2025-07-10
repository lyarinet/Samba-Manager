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
