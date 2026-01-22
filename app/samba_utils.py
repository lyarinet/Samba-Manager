import grp
import os
import pwd
import re
import shlex
import subprocess
import tempfile
from pathlib import Path

# Use local configuration files for development
DEV_MODE = (
    os.environ.get("SAMBA_MANAGER_DEV_MODE", "0") == "1"
)  # Set by environment variable

if DEV_MODE:
    SMB_CONF = "./smb.conf"
    SHARE_CONF = "./shares.conf"
    ACTUAL_SMB_CONF = "/etc/samba/smb.conf"  # Actual Samba config file
else:
    SMB_CONF = "/etc/samba/smb.conf"
    SHARE_CONF = "/etc/samba/shares.conf"
    ACTUAL_SMB_CONF = SMB_CONF


def parse_share_section(content):
    """Parse share sections from a Samba configuration file content"""
    shares = []
    lines = content.split("\n")

    current_share = None
    for line_num, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue

        # Check for share section
        if (
            line.startswith("[")
            and line.endswith("]")
            and not line == "[global]"
            and not line == "[printers]"
            and not line == "[print$]"
        ):
            if current_share:
                shares.append(current_share)
            share_name = line[1:-1]
            current_share = {"name": share_name}
        # Check for parameters within a share
        elif current_share and "=" in line:
            key, value = [x.strip() for x in line.split("=", 1)]
            current_share[key] = value

    # Add the last share if exists
    if current_share:
        shares.append(current_share)

    return shares


def parse_config_content(content):
    """Parse Samba configuration content into sections"""
    sections = {}
    current_section = None

    for line in content.split("\n"):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#") or line.startswith(";"):
            continue

        # Check for section headers
        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip()
            current_section = {}
            sections[section_name] = current_section

        # Check for parameters
        elif "=" in line and current_section is not None:
            parts = line.split("=", 1)
            param_name = parts[0].strip()
            param_value = parts[1].strip()
            current_section[param_name] = param_value

    return sections


# Function to auto-detect share directories
def detect_share_directories():
    """Auto-detect existing share directories on the system"""
    share_dirs = {}

    # Common locations to check for shares
    potential_locations = [
        "/srv/samba",
        "/var/www",
        "/var/lib/samba/shares",
        "/home/shares",
        "/media",
        "/mnt",
        os.path.expanduser("~/samba_manager"),
    ]

    # Check existing shares in Samba config
    if os.path.exists(ACTUAL_SMB_CONF):
        try:
            with open(ACTUAL_SMB_CONF, "r") as f:
                content = f.read()

            # Extract share sections and their paths
            shares = parse_share_section(content)
            for share in shares:
                if "name" in share and "path" in share:
                    if os.path.exists(share["path"]):
                        share_dirs[share["name"]] = share["path"]
        except Exception as e:
            print(f"Error reading Samba config: {e}")

    # Check common locations for potential shares
    for location in potential_locations:
        if os.path.exists(location):
            try:
                # If it's a directory itself, add it
                if os.path.isdir(location):
                    name = os.path.basename(location)
                    if name not in share_dirs:
                        share_dirs[name] = location

                # Check subdirectories
                for item in os.listdir(location):
                    full_path = os.path.join(location, item)
                    if os.path.isdir(full_path) and not item.startswith("."):
                        if item not in share_dirs:
                            share_dirs[item] = full_path
            except Exception as e:
                print(f"Error checking location {location}: {e}")

    # Add some default shares if none found
    if not share_dirs:
        share_dirs = {
            "public": "/srv/samba/public",
            "share": os.path.expanduser("~/samba_manager"),
        }

    return share_dirs


# Get auto-detected share directories
SHARE_DIRS = detect_share_directories()


def check_sudo_access():
    """Check if the application has sudo access to manage Samba"""
    if DEV_MODE:
        return True  # In development mode, we don't need sudo
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True)
        return result.returncode == 0
    except Exception:
        return False


def run_command(cmd, input_str=None):
    """Run a shell command and return the result"""
    try:
        if input_str:
            result = subprocess.run(
                cmd,
                input=input_str.encode(),
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except Exception as e:
        return False, str(e)


def restart_samba_service():
    """Restart Samba service with proper error handling"""
    try:
        # First try systemctl
        print("Attempting to restart Samba services with systemctl")
        systemctl_cmd = ["sudo", "systemctl", "restart", "smbd.service", "nmbd.service"]
        result = subprocess.run(
            systemctl_cmd, capture_output=True, text=True, check=False
        )

        if result.returncode == 0:
            print("Successfully restarted Samba services with systemctl")
            return True

        # If systemctl fails, try service command
        print("systemctl failed, trying service command")
        service_cmd1 = ["sudo", "service", "smbd", "restart"]
        service_cmd2 = ["sudo", "service", "nmbd", "restart"]

        result1 = subprocess.run(
            service_cmd1, capture_output=True, text=True, check=False
        )
        result2 = subprocess.run(
            service_cmd2, capture_output=True, text=True, check=False
        )

        if result1.returncode == 0 and result2.returncode == 0:
            print("Successfully restarted Samba services with service command")
            return True

        # If both methods fail, try init.d scripts
        print("service command failed, trying init.d scripts")
        init_cmd1 = ["sudo", "/etc/init.d/smbd", "restart"]
        init_cmd2 = ["sudo", "/etc/init.d/nmbd", "restart"]

        result1 = subprocess.run(init_cmd1, capture_output=True, text=True, check=False)
        result2 = subprocess.run(init_cmd2, capture_output=True, text=True, check=False)

        if result1.returncode == 0 and result2.returncode == 0:
            print("Successfully restarted Samba services with init.d scripts")
            return True

        print("All methods to restart Samba services failed")
        return False
    except Exception as e:
        print(f"Error restarting Samba service: {e}")
        return False


def get_samba_status():
    """Get the status of the Samba service"""
    if DEV_MODE:
        return {"smbd": "active (dev)", "nmbd": "active (dev)"}
    try:
        # Try systemctl first (for systemd systems)
        smbd = subprocess.run(
            ["systemctl", "is-active", "smbd"], capture_output=True, text=True
        )
        nmbd = subprocess.run(
            ["systemctl", "is-active", "nmbd"], capture_output=True, text=True
        )
        
        # If systemctl works and doesn't give the container error, return the results
        smbd_output = smbd.stdout.strip()
        nmbd_output = nmbd.stdout.strip()
        if not smbd_output.startswith('"systemd" is not running'):
            return {"smbd": smbd_output, "nmbd": nmbd_output}
    except Exception:
        pass
    
    # Fallback to service command for non-systemd environments (like containers)
    try:
        smbd_service = subprocess.run(
            ["service", "smbd", "status"], capture_output=True, text=True
        )
        nmbd_service = subprocess.run(
            ["service", "nmbd", "status"], capture_output=True, text=True
        )
        
        # Parse service command output - return code 0 means running
        smbd_status = "active" if smbd_service.returncode == 0 else "inactive"
        nmbd_status = "active" if nmbd_service.returncode == 0 else "inactive"
        
        return {"smbd": smbd_status, "nmbd": nmbd_status}
    except Exception:
        return {"smbd": "unknown", "nmbd": "unknown"}


def read_global_settings():
    try:
        # Try to read from the system configuration file first
        system_conf = "/etc/samba/smb.conf"
        data = ""

        # Check if we can read the system config
        try:
            # Try to read the system config with sudo if possible
            sudo_check = subprocess.run(
                ["sudo", "-n", "true"], capture_output=True, text=True, check=False
            )

            if sudo_check.returncode == 0:
                # We have sudo access, read the system config
                cat_result = subprocess.run(
                    ["sudo", "cat", system_conf],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if cat_result.returncode == 0:
                    print("Reading settings from system configuration file")
                    data = cat_result.stdout
        except Exception as e:
            print(f"Error reading system config: {e}")

        # If we couldn't read the system config, fall back to the local config
        if not data:
            print("Reading settings from local configuration file")
            with open(SMB_CONF, "r") as f:
                data = f.read()

        # Define default values for all settings
        settings = {
            "server_string": "Samba Server",
            "workgroup": "WORKGROUP",
            "log_level": "1",
            "server_role": "standalone",
            "log_file": "/var/log/samba/log.%m",
            "max_log_size": "1000",
            "security": "user",
            "encrypt_passwords": "yes",
            "guest_account": "nobody",
            "map_to_guest": "Bad User",
            "interfaces": "",
            "bind_interfaces_only": "no",
            "hosts_allow": "",
            "hosts_deny": "",
            "unix_charset": "UTF-8",
            "dos_charset": "CP850",
            "deadtime": "15",
            "keepalive": "300",
            "max_connections": "0",
            "socket_options": "TCP_NODELAY IPTOS_LOWDELAY",
            "dns_proxy": "no",
            "usershare_allow_guests": "yes",
        }

        # Define mappings between our keys and Samba config keys
        mappings = {
            "server_string": r"server string\s*=\s*(.*)",
            "workgroup": r"workgroup\s*=\s*(.*)",
            "log_level": r"log level\s*=\s*(.*)",
            "server_role": r"server role\s*=\s*(.*)",
            "log_file": r"log file\s*=\s*(.*)",
            "max_log_size": r"max log size\s*=\s*(.*)",
            "security": r"security\s*=\s*(.*)",
            "encrypt_passwords": r"encrypt passwords\s*=\s*(.*)",
            "guest_account": r"guest account\s*=\s*(.*)",
            "map_to_guest": r"map to guest\s*=\s*(.*)",
            "interfaces": r"interfaces\s*=\s*(.*)",
            "bind_interfaces_only": r"bind interfaces only\s*=\s*(.*)",
            "hosts_allow": r"hosts allow\s*=\s*(.*)",
            "hosts_deny": r"hosts deny\s*=\s*(.*)",
            "unix_charset": r"unix charset\s*=\s*(.*)",
            "dos_charset": r"dos charset\s*=\s*(.*)",
            "deadtime": r"deadtime\s*=\s*(.*)",
            "keepalive": r"keepalive\s*=\s*(.*)",
            "max_connections": r"max connections\s*=\s*(.*)",
            "socket_options": r"socket options\s*=\s*(.*)",
            "dns_proxy": r"dns proxy\s*=\s*(.*)",
            "usershare_allow_guests": r"usershare allow guests\s*=\s*(.*)",
        }

        # Extract values from the config file
        for key, pattern in mappings.items():
            match = re.search(pattern, data)
            if match:
                settings[key] = match.group(1).strip()

        return settings

    except Exception as e:
        print(f"Error reading global settings: {str(e)}")
        return {
            "error": str(e),
            "server_string": "Samba Server",
            "workgroup": "WORKGROUP",
            "log_level": "1",
            "server_role": "standalone",
            "log_file": "/var/log/samba/log.%m",
            "max_log_size": "1000",
            "security": "user",
            "encrypt_passwords": "yes",
            "guest_account": "nobody",
            "map_to_guest": "Bad User",
            "interfaces": "",
            "bind_interfaces_only": "no",
            "hosts_allow": "",
            "hosts_deny": "",
            "unix_charset": "UTF-8",
            "dos_charset": "CP850",
            "deadtime": "15",
            "keepalive": "300",
            "max_connections": "0",
            "socket_options": "TCP_NODELAY IPTOS_LOWDELAY",
            "dns_proxy": "no",
            "usershare_allow_guests": "yes",
        }


def read_samba_config():
    """Read the content of the Samba configuration file"""
    try:
        with open(SMB_CONF, "r") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading Samba config: {e}")
        return ""


def write_global_settings(settings):
    """Write global settings to the Samba configuration file"""
    try:
        # Get the current configuration
        config_content = read_samba_config()

        # Create a backup of the current config
        backup_path = SMB_CONF + ".bak"
        with open(backup_path, "w") as f:
            f.write(config_content)

        # Parse the configuration into sections
        sections = parse_config_content(config_content)

        # Update the global section
        if "global" in sections:
            global_section = sections["global"]

            # Update the settings
            for key, value in settings.items():
                if value:  # Only update if value is not empty
                    global_section[key] = value
                else:
                    # For empty values, remove the setting from the configuration
                    if key in global_section:
                        del global_section[key]

            # Make sure the include statement is present
            if DEV_MODE:
                global_section["include"] = "./shares.conf"
            else:
                global_section["include"] = "/etc/samba/shares.conf"
        else:
            # Create a new global section if it doesn't exist
            sections["global"] = settings

            # Add the include statement
            if DEV_MODE:
                sections["global"]["include"] = "./shares.conf"
            else:
                sections["global"]["include"] = "/etc/samba/shares.conf"

        # Convert the sections back to a configuration string
        new_config = ""
        for section_name, section_params in sections.items():
            new_config += f"[{section_name}]\n"
            for param_name, param_value in section_params.items():
                new_config += f"    {param_name} = {param_value}\n"
            new_config += "\n"

        # Write the configuration to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write(new_config)
            temp_path = temp_file.name

        success = True

        if DEV_MODE:
            # In dev mode, first update the local configuration file
            local_result = subprocess.run(
                ["cp", temp_path, SMB_CONF], capture_output=True, text=True, check=False
            )

            if local_result.returncode != 0:
                print(f"Error writing to local config: {local_result.stderr}")
                success = False

            # Also try to update the system config if we have sudo access
            try:
                # Check if we have sudo access
                sudo_check = subprocess.run(
                    ["sudo", "-n", "true"], capture_output=True, text=True, check=False
                )

                if sudo_check.returncode == 0:
                    # We have sudo access, update the system config
                    system_result = subprocess.run(
                        ["sudo", "cp", temp_path, "/etc/samba/smb.conf"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if system_result.returncode == 0:
                        print("Updated system Samba configuration")

                        # Also update the system shares.conf
                        with open("./shares.conf", "r") as local_shares:
                            local_shares_content = local_shares.read()

                        with tempfile.NamedTemporaryFile(
                            mode="w", delete=False
                        ) as shares_temp:
                            shares_temp.write(local_shares_content)
                            shares_temp_path = shares_temp.name

                        shares_result = subprocess.run(
                            ["sudo", "cp", shares_temp_path, "/etc/samba/shares.conf"],
                            capture_output=True,
                            text=True,
                            check=False,
                        )

                        os.unlink(shares_temp_path)

                        if shares_result.returncode == 0:
                            print("Updated system shares configuration")

                            # Restart the system services
                            restart_result = subprocess.run(
                                ["sudo", "systemctl", "restart", "smbd", "nmbd"],
                                capture_output=True,
                                text=True,
                                check=False,
                            )

                            if restart_result.returncode == 0:
                                print("Restarted system Samba services")
                            else:
                                print(
                                    f"Failed to restart system services: {restart_result.stderr}"
                                )
                    else:
                        print(f"Failed to update system config: {system_result.stderr}")
                else:
                    print("No sudo access available, skipping system config update")
            except Exception as sudo_error:
                print(f"Error updating system config: {str(sudo_error)}")
                # Continue with local config only
        else:
            # In production mode, use sudo for the system config
            system_result = subprocess.run(
                ["sudo", "cp", temp_path, "/etc/samba/smb.conf"],
                capture_output=True,
                text=True,
                check=False,
            )

            if system_result.returncode != 0:
                print(f"Error writing config: {system_result.stderr}")
                success = False
            else:
                print("Updated system Samba configuration")

                # Also update the local copy for reference
                try:
                    local_result = subprocess.run(
                        ["cp", temp_path, "./smb.conf"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if local_result.returncode == 0:
                        print("Updated local copy of Samba configuration")
                except Exception as e:
                    print(f"Error updating local copy: {str(e)}")

        # Clean up the temporary file
        os.unlink(temp_path)

        if not success:
            return False

        # Validate the configuration
        if DEV_MODE:
            # In dev mode, validate the local config
            validate_cmd = subprocess.run(
                ["testparm", "-s", SMB_CONF],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            # In production mode, validate the system config
            validate_cmd = subprocess.run(
                ["sudo", "testparm", "-s", "/etc/samba/smb.conf"],
                capture_output=True,
                text=True,
                check=False,
            )

        if validate_cmd.returncode != 0:
            # If validation fails, restore the backup
            if DEV_MODE:
                subprocess.run(["cp", backup_path, SMB_CONF], check=False)
            else:
                subprocess.run(
                    ["sudo", "cp", backup_path, "/etc/samba/smb.conf"], check=False
                )
            print(f"Invalid configuration: {validate_cmd.stderr}")
            return False

        # Restart Samba services
        if DEV_MODE:
            # In development mode, we already tried to restart the system services if we had sudo access
            print("Development mode: Local configuration updated successfully")
        else:
            # In production mode, restart the services
            restart_cmd = subprocess.run(
                ["sudo", "systemctl", "restart", "smbd", "nmbd"],
                capture_output=True,
                text=True,
                check=False,
            )

            if restart_cmd.returncode != 0:
                print(f"Error restarting services: {restart_cmd.stderr}")
                return False
            else:
                print("Restarted system Samba services")

        return True
    except Exception as e:
        print(f"Exception in write_global_settings: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def parse_user_group_list(value):
    """Parse a list of users and groups from a Samba config value.
    Returns a tuple of (users_list, groups_list)."""
    if not value:
        return [], []

    items = [item.strip() for item in value.split(",") if item.strip()]
    users = [item for item in items if not item.startswith("@")]
    groups = [item for item in items if item.startswith("@")]

    return users, groups


def format_user_group_list(users, groups):
    """Format users and groups into a single comma-separated string."""
    all_items = []
    if users:
        if isinstance(users, list):
            all_items.extend(users)
        else:
            all_items.append(users)

    if groups:
        if isinstance(groups, list):
            all_items.extend(groups)
        else:
            all_items.append(groups)

    return ",".join(all_items) if all_items else ""


def load_shares():
    """Load Samba shares from the configuration files"""
    shares = []

    # First read from the main configuration file
    if os.path.exists(SMB_CONF):
        print(f"Reading shares from main config {SMB_CONF}")
        try:
            with open(SMB_CONF, "r") as f:
                content = f.read()

            # Parse shares from content
            sections = parse_config_content(content)
            for name, section in sections.items():
                # Skip non-share sections and special shares
                if name in ["global", "printers", "print$"]:
                    continue

                # Create share dictionary with normalized keys
                share = {"name": name}

                # Map Samba config keys to our normalized keys
                key_mapping = {
                    "path": "path",
                    "comment": "comment",
                    "browseable": "browseable",
                    "browsable": "browseable",  # Alternative spelling
                    "read only": "read_only",
                    "guest ok": "guest_ok",
                    "valid users": "valid_users",
                    "write list": "write_list",
                    "create mask": "create_mask",
                    "directory mask": "directory_mask",
                    "force group": "force_group",
                    "max connections": "max_connections",
                }

                # Copy values using the mapping
                for samba_key, our_key in key_mapping.items():
                    if samba_key in section:
                        share[our_key] = section[samba_key]

                # Add default values if not present
                defaults = {
                    "path": "/tmp",
                    "comment": "",
                    "browseable": "yes",
                    "read_only": "no",
                    "guest_ok": "no",
                    "valid_users": "",
                    "write_list": "",
                    "create_mask": "0775",
                    "directory_mask": "0775",
                    "force_group": "smbusers",
                    "max_connections": "0",
                }

                for key, value in defaults.items():
                    if key not in share:
                        share[key] = value

                # If valid_users is empty but write_list has values, use write_list for valid_users
                if not share.get("valid_users") and share.get("write_list"):
                    share["valid_users"] = share["write_list"]
                    print(
                        f"Using write_list as valid_users for share {name}: {share['valid_users']}"
                    )

                # Debug output for valid_users and write_list
                print(
                    f"Share {name} from main config - valid_users: '{share.get('valid_users', '')}', write_list: '{share.get('write_list', '')}'"
                )

                shares.append(share)
        except Exception as e:
            print(f"Error reading shares from main config: {e}")

    # Then read from the shares configuration file
    if os.path.exists(SHARE_CONF):
        print(f"Reading shares from shares config {SHARE_CONF}")
        try:
            with open(SHARE_CONF, "r") as f:
                content = f.read()

            # Parse shares from content
            sections = parse_config_content(content)
            for name, section in sections.items():
                # Skip non-share sections
                if name == "global":
                    continue

                # Check if this share already exists (from main config)
                existing_share = next((s for s in shares if s["name"] == name), None)
                if existing_share:
                    print(
                        f"Share {name} already exists from main config, updating from shares config"
                    )

                    # Map Samba config keys to our normalized keys
                    key_mapping = {
                        "path": "path",
                        "comment": "comment",
                        "browseable": "browseable",
                        "browsable": "browseable",  # Alternative spelling
                        "read only": "read_only",
                        "guest ok": "guest_ok",
                        "valid users": "valid_users",
                        "write list": "write_list",
                        "create mask": "create_mask",
                        "directory mask": "directory_mask",
                        "force group": "force_group",
                        "max connections": "max_connections",
                    }

                    # Update values using the mapping
                    for samba_key, our_key in key_mapping.items():
                        if samba_key in section:
                            existing_share[our_key] = section[samba_key]

                    # If valid_users is empty but write_list has values, use write_list for valid_users
                    if not existing_share.get("valid_users") and existing_share.get(
                        "write_list"
                    ):
                        existing_share["valid_users"] = existing_share["write_list"]
                        print(
                            f"Using write_list as valid_users for existing share {name}: {existing_share['valid_users']}"
                        )

                    # Debug output for valid_users and write_list
                    print(
                        f"Updated share {name} - valid_users: '{existing_share.get('valid_users', '')}', write_list: '{existing_share.get('write_list', '')}'"
                    )
                else:
                    # Create new share dictionary with normalized keys
                    share = {"name": name}

                    # Map Samba config keys to our normalized keys
                    key_mapping = {
                        "path": "path",
                        "comment": "comment",
                        "browseable": "browseable",
                        "browsable": "browseable",  # Alternative spelling
                        "read only": "read_only",
                        "guest ok": "guest_ok",
                        "valid users": "valid_users",
                        "write list": "write_list",
                        "create mask": "create_mask",
                        "directory mask": "directory_mask",
                        "force group": "force_group",
                        "max connections": "max_connections",
                    }

                    # Copy values using the mapping
                    for samba_key, our_key in key_mapping.items():
                        if samba_key in section:
                            share[our_key] = section[samba_key]

                    # Add default values if not present
                    defaults = {
                        "path": "/tmp",
                        "comment": "",
                        "browseable": "yes",
                        "read_only": "no",
                        "guest_ok": "no",
                        "valid_users": "",
                        "write_list": "",
                        "create_mask": "0775",
                        "directory_mask": "0775",
                        "force_group": "smbusers",
                        "max_connections": "0",
                    }

                    for key, value in defaults.items():
                        if key not in share:
                            share[key] = value

                    # If valid_users is empty but write_list has values, use write_list for valid_users
                    if not share.get("valid_users") and share.get("write_list"):
                        share["valid_users"] = share["write_list"]
                        print(
                            f"Using write_list as valid_users for new share {name}: {share['valid_users']}"
                        )

                    # Debug output for valid_users and write_list
                    print(
                        f"Share {name} from shares config - valid_users: '{share.get('valid_users', '')}', write_list: '{share.get('write_list', '')}'"
                    )

                    shares.append(share)
        except Exception as e:
            print(f"Error reading shares from shares config: {e}")

    print(f"Total shares loaded: {len(shares)}")

    # Final check for all shares: ensure valid_users includes write_list users
    for share in shares:
        if share.get("write_list") and not share.get("valid_users"):
            share["valid_users"] = share["write_list"]
            print(
                f"Final check: Using write_list as valid_users for share {share['name']}: {share['valid_users']}"
            )
        elif share.get("write_list") and share.get("valid_users"):
            # Make sure all write_list users are in valid_users
            valid_users_set = set(
                user.strip() for user in share["valid_users"].split(",") if user.strip()
            )
            write_list_set = set(
                user.strip() for user in share["write_list"].split(",") if user.strip()
            )

            # If there are users in write_list not in valid_users, add them
            missing_users = write_list_set - valid_users_set
            if missing_users:
                if share["valid_users"]:
                    share["valid_users"] += "," + ",".join(missing_users)
                else:
                    share["valid_users"] = ",".join(missing_users)
                print(
                    f"Added missing write_list users to valid_users for share {share['name']}: {missing_users}"
                )

        # Debug output for max_connections
        print(
            f"Share {share['name']} - max_connections: '{share.get('max_connections', '0')}'"
        )

        # Parse and store user and group lists separately for UI display
        if "valid_users" in share:
            users, groups = parse_user_group_list(share["valid_users"])
            share["valid_users_list"] = users
            share["valid_groups_list"] = groups

        if "write_list" in share:
            users, groups = parse_user_group_list(share["write_list"])
            share["write_users_list"] = users
            share["write_groups_list"] = groups

    # Print final share information for debugging
    print(f"Loaded {len(shares)} shares from configuration")
    for share in shares:
        print(f"Share: {share['name']} - Path: {share['path']}")
        print(
            f"  valid_users: '{share.get('valid_users', '')}', write_list: '{share.get('write_list', '')}'"
        )
        print(
            f"  create_mask: '{share.get('create_mask', '')}', directory_mask: '{share.get('directory_mask', '')}'"
        )

    return shares


def save_shares(shares):
    try:
        print(f"Saving {len(shares)} shares to {SHARE_CONF}")

        # Map our normalized keys back to Samba config keys
        reverse_key_mapping = {
            "path": "path",
            "comment": "comment",
            "browseable": "browseable",
            "read_only": "read only",
            "guest ok": "guest ok",
            "valid_users": "valid users",
            "write list": "write list",
            "create_mask": "create mask",
            "directory mask": "directory mask",
            "force_group": "force group",
            "max_connections": "max connections",
        }

        # These fields should always be included in the config, even if empty
        required_fields = [
            "path",
            "valid_users",
            "write_list",
            "create_mask",
            "directory_mask",
        ]

        # Create temporary file with new configuration
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write("# Samba shares configuration\n\n")
            for s in shares:
                temp_file.write(f"[{s['name']}]\n")

                # First write required fields
                for our_key in required_fields:
                    if our_key in s:
                        samba_key = reverse_key_mapping.get(our_key, our_key)
                        temp_file.write(f"   {samba_key} = {s[our_key]}\n")

                # Then write the rest of the fields
                for our_key, value in s.items():
                    if (
                        our_key != "name" and our_key not in required_fields
                    ):  # Skip the name and required fields
                        if our_key in reverse_key_mapping:
                            samba_key = reverse_key_mapping[our_key]
                            temp_file.write(f"   {samba_key} = {value}\n")
                        else:
                            # For any keys not in our mapping, write them as-is
                            temp_file.write(f"   {our_key} = {value}\n")

                temp_file.write("\n")
            temp_path = temp_file.name
            print(f"Created temporary file at {temp_path}")

        # Backup original shares file if it exists
        if os.path.exists(SHARE_CONF):
            try:
                subprocess.run(
                    ["sudo", "cp", SHARE_CONF, f"{SHARE_CONF}.bak"], check=True
                )
                print(f"Backed up {SHARE_CONF} to {SHARE_CONF}.bak")
            except Exception as e:
                print(f"Warning: Could not backup shares file: {e}")

        # Use sudo to copy the temporary file to the correct location
        try:
            print(f"Copying temporary file to {SHARE_CONF}")
            subprocess.run(["sudo", "cp", temp_path, SHARE_CONF], check=True)
            # Set proper permissions
            subprocess.run(["sudo", "chmod", "644", SHARE_CONF], check=True)

            # If in production mode, also update the local copy for reference
            if not DEV_MODE:
                try:
                    local_path = "./shares.conf"
                    subprocess.run(["cp", temp_path, local_path], check=True)
                    print(f"Updated local copy at {local_path}")
                except Exception as e:
                    print(f"Warning: Could not update local copy: {e}")

            os.unlink(temp_path)  # Remove the temp file
            print(f"Successfully copied configuration to {SHARE_CONF}")
        except Exception as e:
            print(f"Error copying shares file: {e}")
            return False

        # Check if there are any shares defined directly in the main config
        try:
            if os.path.exists(SMB_CONF):
                print(f"Checking for shares in main config {SMB_CONF}")

                # In production mode, we need to read from the system config
                if not DEV_MODE:
                    system_conf = "/etc/samba/smb.conf"
                    result = subprocess.run(
                        ["sudo", "cat", system_conf],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    content = result.stdout
                else:
                    with open(SMB_CONF, "r") as f:
                        content = f.read()

                # Parse the main config
                sections = parse_config_content(content)
                share_sections = [
                    name
                    for name in sections.keys()
                    if name not in ["global", "printers", "print$"]
                ]

                if share_sections:
                    print(
                        f"Found {len(share_sections)} shares in main config: {', '.join(share_sections)}"
                    )

                    # Create a new main config without the share sections
                    with tempfile.NamedTemporaryFile(
                        mode="w", delete=False
                    ) as temp_file:
                        # First write the global section
                        if "global" in sections:
                            temp_file.write("[global]\n")
                            for key, value in sections["global"].items():
                                temp_file.write(f"   {key} = {value}\n")
                            temp_file.write("\n")

                        # Then write any other special sections
                        for section_name in ["printers", "print$"]:
                            if section_name in sections:
                                temp_file.write(f"[{section_name}]\n")
                                for key, value in sections[section_name].items():
                                    temp_file.write(f"   {key} = {value}\n")
                                temp_file.write("\n")

                        temp_path = temp_file.name
                        print(f"Created temporary main config at {temp_path}")

                    # Backup original main config
                    try:
                        if not DEV_MODE:
                            system_conf = "/etc/samba/smb.conf"
                            subprocess.run(
                                ["sudo", "cp", system_conf, f"{system_conf}.bak"],
                                check=True,
                            )
                            print(f"Backed up {system_conf} to {system_conf}.bak")
                        else:
                            subprocess.run(
                                ["sudo", "cp", SMB_CONF, f"{SMB_CONF}.bak"], check=True
                            )
                            print(f"Backed up {SMB_CONF} to {SMB_CONF}.bak")
                    except Exception as e:
                        print(f"Warning: Could not backup main config: {e}")

                    # Use sudo to copy the temporary file to the correct location
                    if not DEV_MODE:
                        system_conf = "/etc/samba/smb.conf"
                        subprocess.run(
                            ["sudo", "cp", temp_path, system_conf], check=True
                        )
                        # Also update local copy
                        try:
                            subprocess.run(["cp", temp_path, "./smb.conf"], check=True)
                            print(f"Updated local copy of main config")
                        except Exception as e:
                            print(
                                f"Warning: Could not update local copy of main config: {e}"
                            )
                    else:
                        subprocess.run(["sudo", "cp", temp_path, SMB_CONF], check=True)

                    # Set proper permissions
                    if not DEV_MODE:
                        subprocess.run(
                            ["sudo", "chmod", "644", system_conf], check=True
                        )
                    else:
                        subprocess.run(["sudo", "chmod", "644", SMB_CONF], check=True)

                    os.unlink(temp_path)  # Remove the temp file
                    print(f"Successfully removed shares from main config")
        except Exception as e:
            print(f"Warning: Could not check/update main config: {e}")

        # Ensure the include directive exists in the main config
        try:
            # In production mode, we need to read from the system config
            if not DEV_MODE:
                system_conf = "/etc/samba/smb.conf"
                result = subprocess.run(
                    ["sudo", "cat", system_conf],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                content = result.stdout
                include_path = "/etc/samba/shares.conf"
            else:
                with open(SMB_CONF, "r") as f:
                    content = f.read()
                include_path = SHARE_CONF

            if f"include = {include_path}" not in content:
                print(f"Adding include directive to main config")
                # Create a temporary file with updated content
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
                    if "[global]" in content:
                        new_content = content.replace(
                            "[global]", f"[global]\n   include = {include_path}"
                        )
                    else:
                        new_content = (
                            f"[global]\n   include = {include_path}\n\n{content}"
                        )
                    temp_file.write(new_content)
                    temp_path = temp_file.name

                # Use sudo to copy the temporary file to the correct location
                if not DEV_MODE:
                    system_conf = "/etc/samba/smb.conf"
                    subprocess.run(["sudo", "cp", temp_path, system_conf], check=True)
                    # Also update local copy
                    try:
                        subprocess.run(["cp", temp_path, "./smb.conf"], check=True)
                        print(
                            f"Updated local copy of main config with include directive"
                        )
                    except Exception as e:
                        print(
                            f"Warning: Could not update local copy of main config: {e}"
                        )
                else:
                    subprocess.run(["sudo", "cp", temp_path, SMB_CONF], check=True)

                # Set proper permissions
                if not DEV_MODE:
                    subprocess.run(["sudo", "chmod", "644", system_conf], check=True)
                else:
                    subprocess.run(["sudo", "chmod", "644", SMB_CONF], check=True)

                os.unlink(temp_path)  # Remove the temp file
                print(f"Added include directive to main config")
        except Exception as e:
            print(f"Warning: Could not update include directive: {e}")

        # Validate configuration before restarting
        try:
            validate_cmd = ["sudo", "testparm", "-s"]
            validate_result = subprocess.run(
                validate_cmd, capture_output=True, text=True, check=False
            )
            if validate_result.returncode != 0:
                print(
                    f"Warning: Samba configuration validation failed: {validate_result.stderr}"
                )
                # Continue anyway as testparm might have warnings but still be valid
        except Exception as e:
            print(f"Warning: Could not validate configuration: {e}")

        # Restart Samba service
        print("Restarting Samba service")
        result = restart_samba_service()
        print(f"Samba service restart {'successful' if result else 'failed'}")
        return result
    except Exception as e:
        print(f"Error saving shares: {e}")
        return False


def add_or_update_share(new_share):
    """Add or update a Samba share"""
    try:
        print(f"Adding or updating share: {new_share['name']}")

        # Ensure we have all required keys with normalized names
        required_keys = [
            "name",
            "path",
            "browseable",
            "read_only",
            "guest_ok",
            "valid_users",
            "write_list",
            "create_mask",
            "directory_mask",
            "max_connections",
        ]

        # Add default values for missing keys
        defaults = {
            "comment": "",
            "browseable": "yes",
            "read_only": "no",
            "guest_ok": "no",
            "valid_users": "",
            "write_list": "",
            "create_mask": "0775",
            "directory_mask": "0775",
            "max_connections": "0",
        }

        for key, value in defaults.items():
            if key not in new_share or not new_share[key]:
                new_share[key] = value
                print(f"Using default value for {key}: {value}")

        print(f"Processing share with path: {new_share['path']}")

        # Ensure the share directory exists with proper permissions
        if not create_share_directory(new_share["name"], new_share["path"]):
            print(
                f"Failed to create or set permissions on share directory: {new_share['path']}"
            )
            return False

        # Load existing shares
        shares = load_shares()

        # Check if we're updating an existing share
        for idx, s in enumerate(shares):
            if s["name"] == new_share["name"]:
                print(f"Updating existing share: {new_share['name']}")
                shares[idx] = new_share
                break
        else:
            # Share doesn't exist, add it
            print(f"Adding new share: {new_share['name']}")
            shares.append(new_share)

        # Save the updated shares
        result = save_shares(shares)
        if result:
            print(f"Successfully saved share: {new_share['name']}")
        else:
            print(f"Failed to save share: {new_share['name']}")

        return result
    except Exception as e:
        print(f"Error adding or updating share: {e}")
        return False


def delete_share(name):
    """Delete a Samba share by name and restart the service"""
    try:
        print(f"Deleting share: {name}")
        shares = load_shares()
        original_count = len(shares)

        # Filter out the share to delete
        new_shares = [s for s in shares if s["name"] != name]

        if len(new_shares) == original_count:
            print(f"Warning: Share '{name}' not found in configuration")
            return False

        print(f"Removed share '{name}' from configuration")

        # Save the updated shares and restart Samba
        result = save_shares(new_shares)
        if result:
            print(f"Successfully deleted share '{name}' and restarted Samba")
        else:
            print(f"Failed to save configuration after deleting share '{name}'")

        return result
    except Exception as e:
        print(f"Error deleting share: {e}")
        return False


def list_system_users():
    try:
        output = subprocess.check_output(["getent", "passwd"]).decode()
        return [
            line.split(":")[0]
            for line in output.strip().split("\n")
            if int(line.split(":")[2]) >= 1000
        ]
    except Exception:
        return []


def list_system_groups():
    try:
        output = subprocess.check_output(["getent", "group"]).decode()
        return [
            line.split(":")[0]
            for line in output.strip().split("\n")
            if int(line.split(":")[2]) >= 1000
        ]
    except Exception:
        return []


def validate_share_path(path):
    """Validate if a share path exists and is accessible by Samba.
    If the path doesn't exist, attempt to create it."""
    try:
        print(f"Validating share path: {path}")

        # Special handling for home directories
        if path.startswith("/home/"):
            parts = path.split("/")
            if len(parts) >= 3:
                username = parts[2]
                print(f"Path is in home directory of user: {username}")

                # Check if the user exists
                try:
                    import pwd

                    pwd.getpwnam(username)
                    print(f"User {username} exists")

                    # If the path doesn't exist but the user does, we can create it
                    if not os.path.exists(path):
                        print(f"Creating directory in user's home: {path}")
                        # Create the directory with the user as owner
                        mkdir_result = subprocess.run(
                            ["sudo", "mkdir", "-p", path],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        if mkdir_result.returncode != 0:
                            error_msg = (
                                f"Could not create directory: {mkdir_result.stderr}"
                            )
                            print(error_msg)
                            return False, error_msg

                        # Set ownership to the user
                        chown_result = subprocess.run(
                            ["sudo", "chown", "-R", f"{username}:{username}", path],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        if chown_result.returncode != 0:
                            print(
                                f"Warning: Could not set ownership to {username}: {chown_result.stderr}"
                            )

                        # Set permissions
                        chmod_result = subprocess.run(
                            ["sudo", "chmod", "-R", "0755", path],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        if chmod_result.returncode != 0:
                            print(
                                f"Warning: Could not set permissions: {chmod_result.stderr}"
                            )

                        print(f"Successfully created directory in user's home: {path}")
                        return (
                            True,
                            "Path created successfully in user's home directory",
                        )
                except KeyError:
                    print(f"User {username} does not exist")
                    return False, f"User {username} does not exist"

        # Check if path exists
        if not os.path.exists(path):
            print(f"Path {path} does not exist, attempting to create it")

            # Create parent directories first if they don't exist
            parent_dir = os.path.dirname(path)
            if parent_dir and not os.path.exists(parent_dir):
                print(
                    f"Parent directory {parent_dir} does not exist, creating it first"
                )
                parent_result = subprocess.run(
                    ["sudo", "mkdir", "-p", parent_dir],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if parent_result.returncode != 0:
                    error_msg = (
                        f"Could not create parent directory: {parent_result.stderr}"
                    )
                    print(error_msg)
                    return False, error_msg

            # Try to create the directory with sudo
            result = subprocess.run(
                ["sudo", "mkdir", "-p", path],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                error_msg = (
                    f"Path does not exist and could not be created: {result.stderr}"
                )
                print(error_msg)
                return False, error_msg

            # Verify the directory was created
            if not os.path.exists(path):
                error_msg = f"Directory creation command completed but path still doesn't exist: {path}"
                print(error_msg)
                return False, "Path could not be created"

            print(f"Successfully created directory: {path}")

            # Create smbusers group if it doesn't exist
            try:
                grp.getgrnam("smbusers")
                print("smbusers group exists")
            except KeyError:
                print("Creating smbusers group")
                group_result = subprocess.run(
                    ["sudo", "groupadd", "smbusers"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if group_result.returncode != 0:
                    print(
                        f"Warning: Could not create smbusers group: {group_result.stderr}"
                    )

            # Set proper permissions on the new directory
            print(f"Setting ownership for {path}")
            chown_result = subprocess.run(
                ["sudo", "chown", "-R", "root:smbusers", path],
                capture_output=True,
                text=True,
                check=False,
            )
            if chown_result.returncode != 0:
                print(f"Warning: Could not set ownership: {chown_result.stderr}")

            print(f"Setting permissions for {path}")
            chmod_result = subprocess.run(
                ["sudo", "chmod", "-R", "2775", path],
                capture_output=True,
                text=True,
                check=False,
            )
            if chmod_result.returncode != 0:
                print(f"Warning: Could not set permissions: {chmod_result.stderr}")
        else:
            print(f"Path {path} already exists")

        # Check if path is readable
        try:
            # Use sudo to check if the path is readable
            read_result = subprocess.run(
                ["sudo", "test", "-r", path],
                capture_output=True,
                text=True,
                check=False,
            )
            if read_result.returncode != 0:
                error_msg = f"Path is not readable: {path}"
                print(error_msg)
                return False, "Path is not readable"
        except Exception as e:
            print(f"Error checking read access: {e}")
            # Fall back to direct check if sudo test fails
            if not os.access(path, os.R_OK):
                error_msg = f"Path is not readable (direct check): {path}"
                print(error_msg)
                return False, "Path is not readable"

        # Check if path is writable
        try:
            # Use sudo to check if the path is writable
            write_result = subprocess.run(
                ["sudo", "test", "-w", path],
                capture_output=True,
                text=True,
                check=False,
            )
            if write_result.returncode != 0:
                error_msg = f"Path is not writable: {path}"
                print(error_msg)
                return False, "Path is not writable"
        except Exception as e:
            print(f"Error checking write access: {e}")
            # Fall back to direct check if sudo test fails
            if not os.access(path, os.W_OK):
                error_msg = f"Path is not writable (direct check): {path}"
                print(error_msg)
                return False, "Path is not writable"

        print(f"Path validation successful for {path}")
        return True, "Path is valid and accessible"
    except Exception as e:
        error_msg = f"Error validating share path: {e}"
        print(error_msg)
        return False, f"Error validating path: {str(e)}"


def export_config():
    """Export the complete Samba configuration as a single file"""
    try:
        # Read the main config
        with open(SMB_CONF, "r") as f:
            main_config = f.read()

        # Read the shares config
        shares_config = ""
        if os.path.exists(SHARE_CONF):
            with open(SHARE_CONF, "r") as f:
                shares_config = f.read()

        # Combine them into a single valid configuration
        # Remove any include statements from main config and append shares
        lines = main_config.split('\n')
        filtered_lines = []
        for line in lines:
            if not line.strip().startswith('include'):
                filtered_lines.append(line)

        combined_config = '\n'.join(filtered_lines)
        if shares_config.strip():
            combined_config += '\n' + shares_config

        return combined_config
    except Exception as e:
        return f"Error exporting configuration: {str(e)}"


def import_config(data):
    """Import a complete Samba configuration file"""
    try:
        # Parse the configuration to separate global and shares
        lines = data.split('\n')
        global_section = []
        shares_section = []
        current_section = None

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('[global]'):
                current_section = 'global'
                global_section.append(line)
            elif stripped.startswith('[') and stripped.endswith(']') and stripped != '[global]':
                current_section = 'shares'
                shares_section.append(line)
            else:
                if current_section == 'global':
                    global_section.append(line)
                elif current_section == 'shares':
                    shares_section.append(line)
                else:
                    # Lines before any section go to global
                    global_section.append(line)

        # Backup original files
        if os.path.exists(SMB_CONF):
            with open(f"{SMB_CONF}.bak", "w") as f_bak:
                with open(SMB_CONF, "r") as f_orig:
                    f_bak.write(f_orig.read())

        if os.path.exists(SHARE_CONF):
            with open(f"{SHARE_CONF}.bak", "w") as f_bak:
                with open(SHARE_CONF, "r") as f_orig:
                    f_bak.write(f_orig.read())

        # Write the global section
        with open(SMB_CONF, "w") as f:
            f.write('\n'.join(global_section))

        # Write the shares section
        with open(SHARE_CONF, "w") as f:
            f.write('\n'.join(shares_section))

        # Restart Samba service
        return restart_samba_service()
    except Exception as e:
        print(f"Error importing configuration: {e}")
        return False


# User Management Functions


def get_samba_users():
    """Get list of Samba users with their status"""
    if DEV_MODE:
        # Try to get real users even in dev mode if possible
        try:
            # Try pdbedit first
            success, output = run_command(["pdbedit", "-L"])
            if success and output.strip():
                users = []
                for line in output.strip().split("\n"):
                    if line.strip():
                        parts = line.split(":")
                        if len(parts) >= 1:
                            username = parts[0].strip()
                            users.append(
                                {
                                    "username": username,
                                    "enabled": True,  # Assume enabled by default
                                    "flags": "U",
                                }
                            )
                return users

            # Try smbpasswd -s command
            success, output = run_command(["cat", "/etc/samba/smbpasswd"])
            if success and output.strip():
                users = []
                for line in output.strip().split("\n"):
                    if line.strip() and not line.startswith("#"):
                        parts = line.split(":")
                        if len(parts) >= 1:
                            username = parts[0].strip()
                            users.append(
                                {"username": username, "enabled": True, "flags": "U"}
                            )
                return users

            # Return mock data if all else fails
            return [
                {"username": "user1", "enabled": True, "flags": "U"},
                {"username": "user2", "enabled": False, "flags": "UD"},
            ]
        except Exception:
            # Return mock data if there's an error
            return [
                {"username": "user1", "enabled": True, "flags": "U"},
                {"username": "user2", "enabled": False, "flags": "UD"},
            ]

    try:
        # First try pdbedit with sudo
        success, output = run_command(["sudo", "pdbedit", "-L"])
        if success and output.strip():
            users = []
            for line in output.strip().split("\n"):
                if line.strip():
                    parts = line.split(":")
                    if len(parts) >= 1:
                        username = parts[0].strip()
                        # Get detailed info for this user
                        detail_success, detail_output = run_command(
                            ["sudo", "pdbedit", "-v", "-u", username]
                        )
                        enabled = True
                        flags = "U"
                        if detail_success:
                            for detail_line in detail_output.split("\n"):
                                if "Account Flags:" in detail_line:
                                    flags = detail_line.split(":", 1)[1].strip()
                                    enabled = "D" not in flags
                        users.append(
                            {"username": username, "enabled": enabled, "flags": flags}
                        )
            return users

        # If pdbedit fails, try reading smbpasswd file directly
        success, output = run_command(["sudo", "cat", "/etc/samba/smbpasswd"])
        if success and output.strip():
            users = []
            for line in output.strip().split("\n"):
                if line.strip() and not line.startswith("#"):
                    parts = line.split(":")
                    if len(parts) >= 1:
                        username = parts[0].strip()
                        # Check if user is disabled (has 'D' flag)
                        disabled = len(parts) > 4 and "D" in parts[4]
                        users.append(
                            {
                                "username": username,
                                "enabled": not disabled,
                                "flags": parts[4] if len(parts) > 4 else "U",
                            }
                        )
            return users

        # If all else fails, return empty list instead of system users
        # System users are not necessarily Samba users
        return []
    except Exception as e:
        print(f"Error getting Samba users: {e}")
        return []


def add_samba_user(username, password, create_system_user=False):
    """Add a new Samba user"""
    if DEV_MODE:
        print(f"[DEV MODE] Would add Samba user: {username}")
        return True

    try:
        # Check if system user exists
        check_user = subprocess.run(
            ["id", username], capture_output=True, text=True, check=False
        )
        user_exists = check_user.returncode == 0

        # Create system user if requested and doesn't exist
        if not user_exists and create_system_user:
            print(f"Creating system user: {username}")
            create_user = subprocess.run(
                ["sudo", "useradd", "-m", "-s", "/bin/bash", username],
                capture_output=True,
                text=True,
                check=False,
            )
            if create_user.returncode != 0:
                print(f"Failed to create system user: {create_user.stderr}")
                return False

            # Set system password
            set_pass = subprocess.Popen(
                ["sudo", "chpasswd"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = set_pass.communicate(input=f"{username}:{password}")
            if set_pass.returncode != 0:
                print(f"Failed to set system password: {stderr}")
                return False

        # Create smbusers group if it doesn't exist
        check_group = subprocess.run(
            ["getent", "group", "smbusers"], capture_output=True, text=True, check=False
        )
        if check_group.returncode != 0:
            print("Creating smbusers group")
            create_group = subprocess.run(
                ["sudo", "groupadd", "smbusers"],
                capture_output=True,
                text=True,
                check=False,
            )
            if create_group.returncode != 0:
                print(f"Failed to create smbusers group: {create_group.stderr}")

        # If the user exists, add them to smbusers group
        if user_exists or create_system_user:
            print(f"Adding {username} to smbusers group")
            add_to_group = subprocess.run(
                ["sudo", "usermod", "-aG", "smbusers", username],
                capture_output=True,
                text=True,
                check=False,
            )
            if add_to_group.returncode != 0:
                print(f"Failed to add user to smbusers group: {add_to_group.stderr}")

        # Add Samba user
        print(f"Creating Samba user: {username}")
        process = subprocess.Popen(
            ["sudo", "smbpasswd", "-s", "-a", username],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout, stderr = process.communicate(input=f"{password}\n{password}\n")

        if process.returncode != 0:
            print(f"Failed to create Samba user: {stderr}")
            return False

        # Enable the Samba user
        print("Enabling Samba user")
        enable = subprocess.run(
            ["sudo", "smbpasswd", "-e", username],
            capture_output=True,
            text=True,
            check=False,
        )

        if enable.returncode != 0:
            print(f"Failed to enable Samba user: {enable.stderr}")
            return False

        return True
    except Exception as e:
        print(f"Error adding Samba user: {e}")
        return False


def remove_samba_user(username, delete_system_user=False):
    """Remove a Samba user"""
    if DEV_MODE:
        print(f"[DEV MODE] Would remove Samba user: {username}")
        return True

    try:
        # Delete Samba user
        success, _ = run_command(["sudo", "smbpasswd", "-x", username])

        # Delete system user if requested
        if delete_system_user:
            run_command(["sudo", "userdel", "-r", username])

        return success
    except Exception as e:
        print(f"Error removing Samba user: {e}")
        return False


def enable_samba_user(username):
    """Enable a Samba user"""
    if DEV_MODE:
        print(f"[DEV MODE] Would enable Samba user: {username}")
        return True

    try:
        success, _ = run_command(["sudo", "smbpasswd", "-e", username])
        return success
    except Exception as e:
        print(f"Error enabling Samba user: {e}")
        return False


def disable_samba_user(username):
    """Disable a Samba user"""
    if DEV_MODE:
        print(f"[DEV MODE] Would disable Samba user: {username}")
        return True

    try:
        success, _ = run_command(["sudo", "smbpasswd", "-d", username])
        return success
    except Exception as e:
        print(f"Error disabling Samba user: {e}")
        return False


def reset_samba_password(username, password):
    """Reset a Samba user's password"""
    if DEV_MODE:
        print(f"[DEV MODE] Would reset password for Samba user: {username}")
        return True

    try:
        success, _ = run_command(
            ["sudo", "smbpasswd", "-s", username], f"{password}\n{password}\n"
        )
        return success
    except Exception as e:
        print(f"Error resetting Samba password: {e}")
        return False


# Setup and Maintenance Functions


def ensure_samba_installed():
    """Ensure Samba is installed"""
    if DEV_MODE:
        return True

    try:
        # Check if smbd is installed
        success, _ = run_command(["which", "smbd"])
        if success:
            return True

        # Install Samba
        success, _ = run_command(["sudo", "apt-get", "update"])
        if not success:
            return False

        success, _ = run_command(
            ["sudo", "apt-get", "install", "-y", "samba", "samba-common-bin"]
        )
        return success
    except Exception as e:
        print(f"Error installing Samba: {e}")
        return False


def create_share_directory(name, path):
    """Create a share directory with proper permissions"""
    if DEV_MODE:
        # In dev mode, just create the directory locally
        os.makedirs(path, exist_ok=True)
        return True

    try:
        print(f"Creating or ensuring share directory exists: {path}")

        # First validate the path - this will create it if needed
        valid, message = validate_share_path(path)
        if not valid:
            print(f"Failed to validate/create share path: {message}")
            return False

        print(f"Path validation successful: {message}")

        # Double-check that the directory exists after validation
        if not os.path.exists(path):
            print(f"Error: Path {path} still doesn't exist after validation")
            return False

        # Set additional share-specific permissions if needed
        # For example, you might want to set specific ACLs or extended attributes

        # Verify the directory is properly set up
        print(f"Successfully created/updated share directory: {path}")
        return True
    except Exception as e:
        print(f"Error creating share directory: {e}")
        return False


def add_users_to_smbusers_group():
    """Add all system users to the smbusers group"""
    if DEV_MODE:
        return True

    try:
        # Create smbusers group if it doesn't exist
        try:
            grp.getgrnam("smbusers")
        except KeyError:
            run_command(["sudo", "groupadd", "smbusers"])

        # Get all system users
        users = list_system_users()

        # Add each user to the smbusers group
        for user in users:
            run_command(["sudo", "usermod", "-aG", "smbusers", user])

        return True
    except Exception as e:
        print(f"Error adding users to smbusers group: {e}")
        return False


def fix_share_permissions():
    """Fix permissions on all share directories"""
    if DEV_MODE:
        return True

    try:
        # Create smbusers group if it doesn't exist
        try:
            grp.getgrnam("smbusers")
        except KeyError:
            run_command(["sudo", "groupadd", "smbusers"])

        # Auto-detect share directories
        share_directories = detect_share_directories()

        # Fix permissions on detected share directories
        for name, path in share_directories.items():
            create_share_directory(name, path)

        return True
    except Exception as e:
        print(f"Error fixing share permissions: {e}")
        return False


def setup_samba():
    """Complete Samba setup"""
    if DEV_MODE:
        print("[DEV MODE] Would set up Samba")
        return True

    try:
        # Install Samba if needed
        if not ensure_samba_installed():
            return False

        # Create smbusers group
        try:
            grp.getgrnam("smbusers")
        except KeyError:
            run_command(["sudo", "groupadd", "smbusers"])

        # Add users to smbusers group
        add_users_to_smbusers_group()

        # Auto-detect share directories
        share_directories = detect_share_directories()

        # Create share directories
        for name, path in share_directories.items():
            create_share_directory(name, path)

        # Configure global settings
        write_global_settings(
            {
                "server string": "Samba Server",
                "workgroup": "WORKGROUP",
                "log level": "1",
            }
        )

        # Create shares based on auto-detected directories
        for name, path in share_directories.items():
            add_or_update_share(
                {
                    "name": name,
                    "path": path,
                    "read only": "no",
                    "valid users": "@smbusers",
                    "guest ok": "no",
                    "browseable": "yes",
                    "create mask": "0770",
                    "directory mask": "0770",
                    "force group": "smbusers",
                    "force user": "root",
                }
            )

        # Enable and restart Samba services
        run_command(["sudo", "systemctl", "enable", "smbd"])
        run_command(["sudo", "systemctl", "enable", "nmbd"])
        restart_samba_service()

        return True
    except Exception as e:
        print(f"Error setting up Samba: {e}")
        return False


def get_samba_installation_status():
    """Get the status of the Samba installation"""
    status = {
        "installed": False,
        "running": False,
        "configured": False,
        "shares": [],
        "users": [],
    }

    try:
        # Check if Samba is installed
        success, _ = run_command(["which", "smbd"])
        status["installed"] = success

        if not success:
            return status

        # Check if Samba is running
        samba_status = get_samba_status()
        status["running"] = samba_status["smbd"] == "active"

        # Check if Samba is configured
        status["configured"] = os.path.exists(ACTUAL_SMB_CONF)

        # Get shares
        status["shares"] = load_shares()

        # Get users
        status["users"] = get_samba_users()

        return status
    except Exception as e:
        print(f"Error getting Samba installation status: {e}")
        return status


def create_system_group(group_name):
    """Create a system group"""
    if DEV_MODE:
        print(f"[DEV MODE] Would create system group: {group_name}")
        return True

    try:
        # Validate group name - must start with a letter and contain only letters, numbers, and underscore
        import re

        if not re.match(r"^[a-z][\w-]*$", group_name):
            print(
                f"Invalid group name: {group_name} - Group names must start with a letter and contain only letters, numbers, hyphens, and underscores"
            )
            return False

        # Check if the group already exists
        try:
            grp.getgrnam(group_name)
            print(f"Group {group_name} already exists")
            return True
        except KeyError:
            pass  # Group doesn't exist, continue

        # Create the group
        print(f"Creating system group: {group_name}")
        result = subprocess.run(
            ["sudo", "groupadd", group_name],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"Error creating group: {result.stderr}")
            return False

        print(f"Successfully created group: {group_name}")
        return True
    except Exception as e:
        print(f"Error creating system group: {e}")
        return False


def delete_system_group(group_name):
    """Delete a system group"""
    if DEV_MODE:
        print(f"[DEV MODE] Would delete system group: {group_name}")
        return True

    try:
        # Check if the group exists
        try:
            grp.getgrnam(group_name)
        except KeyError:
            print(f"Group {group_name} does not exist")
            return False

        # Check if the group is a primary group for any user
        import pwd

        primary_users = []
        for user in pwd.getpwall():
            if user.pw_gid == grp.getgrnam(group_name).gr_gid:
                primary_users.append(user.pw_name)

        if primary_users:
            print(
                f"Group {group_name} is the primary group for user(s): {', '.join(primary_users)}"
            )

            # Try to find a suitable alternative group
            try:
                # Try to use 'users' group if it exists
                alt_group = "users"
                grp.getgrnam(alt_group)

                # Change primary group for each user
                for username in primary_users:
                    print(
                        f"Changing primary group for user {username} from {group_name} to {alt_group}"
                    )
                    result = subprocess.run(
                        ["sudo", "usermod", "-g", alt_group, username],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode != 0:
                        print(
                            f"Error changing primary group for user {username}: {result.stderr}"
                        )
                        return False
                    print(f"Successfully changed primary group for user {username}")
            except KeyError:
                # If 'users' group doesn't exist, create it
                print(f"Creating alternative group 'users'")
                create_result = subprocess.run(
                    ["sudo", "groupadd", "users"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if create_result.returncode != 0:
                    print(f"Error creating alternative group: {create_result.stderr}")
                    return False

                # Change primary group for each user
                for username in primary_users:
                    print(
                        f"Changing primary group for user {username} from {group_name} to users"
                    )
                    result = subprocess.run(
                        ["sudo", "usermod", "-g", "users", username],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode != 0:
                        print(
                            f"Error changing primary group for user {username}: {result.stderr}"
                        )
                        return False
                    print(f"Successfully changed primary group for user {username}")

        # Delete the group
        print(f"Deleting system group: {group_name}")
        result = subprocess.run(
            ["sudo", "groupdel", group_name],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"Error deleting group: {result.stderr}")
            return False

        print(f"Successfully deleted group: {group_name}")
        return True
    except Exception as e:
        print(f"Error deleting system group: {e}")
        return False


def get_disk_usage(share_path):
    """Get disk usage information for a share path"""
    try:
        # Use subprocess to run df command
        result = subprocess.run(
            ["df", "-h", share_path], capture_output=True, text=True, check=True
        )

        # Parse the output
        lines = result.stdout.strip().split("\n")
        if len(lines) < 2:
            return None

        # Get headers and values
        headers = lines[0].split()
        values = lines[1].split()

        # Create a dictionary with the disk usage information
        usage_info = {
            "filesystem": values[0],
            "size": values[1],
            "used": values[2],
            "available": values[3],
            "use_percent": values[4],
            "mounted_on": values[5] if len(values) > 5 else "",
        }

        return usage_info
    except Exception as e:
        print(f"Error getting disk usage for {share_path}: {str(e)}")
        return None


def terminate_connection(pid):
    """Terminate a Samba connection by PID"""
    try:
        # Validate PID is numeric
        try:
            pid_num = int(pid)
            if pid_num <= 0:
                return False, f"Invalid PID: {pid} - must be a positive number"
        except ValueError:
            return False, f"Invalid PID: {pid} - not a number"

        # Use the numeric PID for all operations
        pid = str(pid_num)

        # Verify that the PID belongs to a Samba process
        result = subprocess.run(
            ["sudo", "ps", "-p", pid, "-o", "comm="],
            capture_output=True,
            text=True,
            check=False,
        )

        # Check if this is a smbd process
        process_name = result.stdout.strip()
        if not process_name or "smbd" not in process_name:
            return False, f"Process {pid} is not a Samba connection or doesn't exist"

        # First try to get the machine name associated with this PID
        machine_name = None
        try:
            # Get smbstatus output
            status_result = subprocess.run(
                ["sudo", "smbstatus"], capture_output=True, text=True, check=False
            )

            if status_result.returncode == 0:
                # Parse output to find the machine associated with this PID
                lines = status_result.stdout.strip().split("\n")
                for line in lines:
                    if pid in line and ("Service" not in line and "PID" not in line):
                        parts = line.split()
                        if len(parts) > 2:
                            # Extract machine name (typically the 3rd column)
                            machine_name = parts[2]
                            break
        except Exception as e:
            print(f"Error getting machine name for PID {pid}: {str(e)}")

        # Try to kill the process with SIGTERM first
        kill_result = subprocess.run(
            ["sudo", "kill", "-TERM", pid], capture_output=True, text=True, check=False
        )

        # Check if the process is still running
        check_result = subprocess.run(
            ["sudo", "ps", "-p", pid], capture_output=True, text=True, check=False
        )

        # If process still exists, try SIGKILL
        if check_result.returncode == 0:
            print(f"Process {pid} still running after SIGTERM, trying SIGKILL")
            kill_result = subprocess.run(
                ["sudo", "kill", "-KILL", pid],
                capture_output=True,
                text=True,
                check=False,
            )

        # If we have a machine name, also try to disconnect using smbcontrol
        if machine_name:
            try:
                print(f"Attempting to force disconnect machine: {machine_name}")
                # Use smbcontrol to force disconnect the client
                smbcontrol_result = subprocess.run(
                    ["sudo", "smbcontrol", "smbd", "close-share", machine_name],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if smbcontrol_result.returncode != 0:
                    print(f"smbcontrol error: {smbcontrol_result.stderr}")
            except Exception as e:
                print(f"Error using smbcontrol: {str(e)}")

        # Final check if the process is still running
        final_check = subprocess.run(
            ["sudo", "ps", "-p", pid], capture_output=True, text=True, check=False
        )

        if final_check.returncode == 0:
            return (
                False,
                f"Failed to terminate connection {pid} - process still running",
            )

        return True, f"Connection {pid} terminated successfully"
    except Exception as e:
        print(f"Error terminating connection: {str(e)}")
        return False, f"Error terminating connection: {str(e)}"


def terminate_connection_by_machine(machine):
    """Terminate a Samba connection by machine name/IP"""
    try:
        if not machine:
            return False, "No machine name provided"

        # Try to use smbcontrol to force disconnect the client
        try:
            print(f"Attempting to force disconnect machine: {machine}")
            # Use smbcontrol to force disconnect the client
            smbcontrol_result = subprocess.run(
                ["sudo", "smbcontrol", "smbd", "close-share", machine],
                capture_output=True,
                text=True,
                check=False,
            )
            if smbcontrol_result.returncode != 0:
                print(f"smbcontrol error: {smbcontrol_result.stderr}")
                return (
                    False,
                    f"Failed to disconnect {machine}: {smbcontrol_result.stderr}",
                )
        except Exception as e:
            print(f"Error using smbcontrol: {str(e)}")
            return False, f"Error disconnecting {machine}: {str(e)}"

        # Also try to find and kill the associated PID
        try:
            # Get smbstatus output
            status_result = subprocess.run(
                ["sudo", "smbstatus"], capture_output=True, text=True, check=False
            )

            if status_result.returncode == 0:
                # Parse output to find PIDs associated with this machine
                lines = status_result.stdout.strip().split("\n")
                pids_to_kill = []

                for line in lines:
                    if machine in line and (
                        "Service" not in line and "PID" not in line
                    ):
                        parts = line.split()
                        if len(parts) > 2:
                            # Extract PID (typically the 2nd column in connection list)
                            for part in parts:
                                try:
                                    pid = int(part)
                                    pids_to_kill.append(str(pid))
                                    break
                                except ValueError:
                                    continue

                # Kill all PIDs associated with this machine
                for pid in pids_to_kill:
                    print(f"Killing PID {pid} associated with machine {machine}")
                    subprocess.run(["sudo", "kill", "-KILL", pid], check=False)
        except Exception as e:
            print(f"Error killing PIDs for machine {machine}: {str(e)}")

        return True, f"Connection from {machine} terminated successfully"
    except Exception as e:
        print(f"Error terminating connection for machine {machine}: {str(e)}")
        return False, f"Error terminating connection: {str(e)}"


def get_active_connections():
    """Get active Samba connections"""
    try:
        # Use smbstatus to get active connections
        result = subprocess.run(
            ["sudo", "smbstatus"], capture_output=True, text=True, check=True
        )

        output = result.stdout.strip()

        # Process the version information (first line)
        lines = output.split("\n")
        samba_version = lines[0].strip() if lines else "Unknown Samba version"

        # Parse the process list section (first table with PIDs, Username, etc.)
        processes = []
        in_process_section = False
        process_headers_found = False

        # Parse the connection information (second table with Service, PID, etc.)
        connections = []
        in_connections_section = False
        connections_headers_found = False

        # Process each line to extract both tables
        for i, line in enumerate(lines):
            # Skip empty lines
            if not line.strip():
                continue

            # Look for the process list section headers
            if (
                "PID" in line
                and "Username" in line
                and "Group" in line
                and not process_headers_found
            ):
                in_process_section = True
                process_headers_found = True
                continue

            # Skip separator lines after headers
            if (
                in_process_section
                and not processes
                and ("----------" in line or "-------" in line)
            ):
                continue

            # Look for the connection section headers
            if (
                "Service" in line
                and "pid" in line
                and "Machine" in line
                and not connections_headers_found
            ):
                in_process_section = False
                in_connections_section = True
                connections_headers_found = True
                continue

            # Skip separator lines after headers
            if (
                in_connections_section
                and not connections
                and ("----------" in line or "-------" in line)
            ):
                continue

            # End of connection section when we hit "Locked files:" or another section
            if "Locked files:" in line:
                in_connections_section = False
                continue

            # Parse process list entries
            if in_process_section and line.strip():
                # Parse process details
                parts = line.split()
                if len(parts) >= 3:
                    # Validate that PID is numeric
                    pid = parts[0]
                    try:
                        pid_num = int(pid)
                    except ValueError:
                        pid = None

                    # Extract machine name and IP if available
                    machine = parts[3] if len(parts) > 3 else ""
                    machine_ip = ""

                    # Extract IP address if it's in the format machine (ipv4:x.x.x.x)
                    if machine and "(" in machine and "ipv4:" in machine:
                        try:
                            ip_part = (
                                machine.split("(ipv4:")[1].split(")")[0].split(":")[0]
                            )
                            if ip_part:
                                machine_ip = ip_part
                        except:
                            pass

                    process = {
                        "pid": pid,
                        "username": parts[1] if len(parts) > 1 else "",
                        "group": parts[2] if len(parts) > 2 else "",
                        "machine": machine,
                        "machine_ip": machine_ip,
                        "protocol": parts[4] if len(parts) > 4 else "",
                        "version": parts[5] if len(parts) > 5 else "",
                        "encryption": parts[6] if len(parts) > 6 else "",
                        "signing": parts[7] if len(parts) > 7 else "",
                    }
                    processes.append(process)

            # Parse connection entries
            if in_connections_section and line.strip():
                # Parse connection details - typically 4 columns: Service, pid, Machine, Connected at
                parts = line.split(
                    None, 3
                )  # Split at most 3 times to keep the timestamp as one field
                if len(parts) >= 3:
                    # Validate that PID is numeric
                    pid = parts[1]
                    try:
                        pid_num = int(pid)
                    except ValueError:
                        pid = None

                    # Extract machine name and IP if available
                    machine = parts[2] if len(parts) > 2 else ""
                    machine_ip = ""

                    # Extract IP address if it's in the format machine (ipv4:x.x.x.x)
                    if machine and "(" in machine and "ipv4:" in machine:
                        try:
                            ip_part = (
                                machine.split("(ipv4:")[1].split(")")[0].split(":")[0]
                            )
                            if ip_part:
                                machine_ip = ip_part
                        except:
                            pass

                    connection = {
                        "service": parts[0],
                        "pid": pid,
                        "machine": machine,
                        "machine_ip": machine_ip,
                        "connected_at": parts[3] if len(parts) > 3 else "",
                    }
                    connections.append(connection)

        return {
            "version": samba_version,
            "processes": processes,
            "connections": connections,
        }
    except Exception as e:
        print(f"Error getting active connections: {str(e)}")
        return {
            "version": "Error retrieving Samba information",
            "processes": [],
            "connections": [],
        }


def get_share_usage_stats():
    """Get usage statistics for all shares"""
    shares = load_shares()
    stats = []

    for share in shares:
        path = share.get("path", "")
        if path and os.path.exists(path):
            usage = get_disk_usage(path)
            if usage:
                stats.append(
                    {"name": share.get("name", ""), "path": path, "usage": usage}
                )

    return stats


def list_backups():
    """List all available backups"""
    try:
        backup_dir = "/var/lib/samba_manager/backups"

        # Create backup directory if it doesn't exist (with sudo)
        if not os.path.exists(backup_dir):
            subprocess.run(["sudo", "mkdir", "-p", backup_dir], check=True)
            subprocess.run(["sudo", "chmod", "755", backup_dir], check=True)
            return []

        # Get a list of all backup files
        backup_files = []
        for file in os.listdir(backup_dir):
            if file.startswith("samba_backup_") and file.endswith(".tar.gz"):
                file_path = os.path.join(backup_dir, file)
                file_stat = os.stat(file_path)

                # Parse timestamp from filename
                timestamp_str = file.replace("samba_backup_", "").replace(".tar.gz", "")
                try:
                    import datetime

                    timestamp = datetime.datetime.strptime(
                        timestamp_str, "%Y%m%d_%H%M%S"
                    )
                    formatted_date = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    formatted_date = "Unknown Date"

                backup_files.append(
                    {
                        "filename": file,
                        "path": file_path,
                        "size": file_stat.st_size,
                        "date": formatted_date,
                    }
                )

        # Sort by date (newest first)
        backup_files.sort(key=lambda x: x["filename"], reverse=True)

        return backup_files
    except Exception as e:
        print(f"Error listing backups: {e}")
        return []


def create_backup():
    """Create a backup of Samba configuration files"""
    try:
        # Create a timestamp for the backup filename
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = "/var/lib/samba_manager/backups"
        backup_file = f"{backup_dir}/samba_backup_{timestamp}.tar.gz"

        # Create backup directory if it doesn't exist (with sudo)
        subprocess.run(["sudo", "mkdir", "-p", backup_dir], check=True)
        # Set proper permissions on the backup directory
        subprocess.run(["sudo", "chmod", "755", backup_dir], check=True)

        # Files to backup
        backup_files = [
            SMB_CONF,
            SHARE_CONF,
            "/etc/samba/passdb.tdb",
            "/etc/passwd",
            "/etc/group",
            "/etc/shadow",
            "/etc/gshadow",
        ]

        # Create a temporary directory to store files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy files to the temporary directory
            for file_path in backup_files:
                if os.path.exists(file_path):
                    # Extract just the filename without the path
                    file_name = os.path.basename(file_path)
                    # Use sudo to copy the file
                    subprocess.run(
                        ["sudo", "cp", file_path, f"{temp_dir}/{file_name}"], check=True
                    )
                    # Change ownership of the copied file to be readable
                    subprocess.run(
                        ["sudo", "chmod", "644", f"{temp_dir}/{file_name}"], check=True
                    )

            # Create the tar.gz archive
            subprocess.run(
                ["sudo", "tar", "-czf", backup_file, "-C", temp_dir, "."], check=True
            )

            # Change permissions on the backup file
            subprocess.run(["sudo", "chmod", "644", backup_file], check=True)

        return True, backup_file
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False, str(e)


def restore_backup(backup_file):
    """Restore a Samba configuration from a backup file"""
    try:
        # Create a temporary directory to extract files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract the backup archive
            subprocess.run(
                ["sudo", "tar", "-xzf", backup_file, "-C", temp_dir], check=True
            )

            # Files to restore (must match files backed up in create_backup)
            restore_mappings = {
                "smb.conf": SMB_CONF,
                "shares.conf": SHARE_CONF,
                "passdb.tdb": "/etc/samba/passdb.tdb",
                "passwd": "/etc/passwd",
                "group": "/etc/group",
                "shadow": "/etc/shadow",
                "gshadow": "/etc/gshadow",
            }

            # Restore each file
            for src_name, dest_path in restore_mappings.items():
                src_path = os.path.join(temp_dir, src_name)
                if os.path.exists(src_path):
                    # Backup the current file before overwriting
                    if os.path.exists(dest_path):
                        backup_path = f"{dest_path}.bak"
                        subprocess.run(
                            ["sudo", "cp", "-f", dest_path, backup_path], check=True
                        )

                    # Copy the restored file to its proper location
                    subprocess.run(
                        ["sudo", "cp", "-f", src_path, dest_path], check=True
                    )

                    # Set proper permissions
                    if src_name in ["passwd", "group"]:
                        subprocess.run(["sudo", "chmod", "644", dest_path], check=True)
                    elif src_name in ["shadow", "gshadow"]:
                        subprocess.run(["sudo", "chmod", "600", dest_path], check=True)
                    else:
                        subprocess.run(["sudo", "chmod", "644", dest_path], check=True)

        # Restart Samba services
        restart_samba_service()

        return True, "Backup restored successfully"
    except Exception as e:
        print(f"Error restoring backup: {e}")
        return False, str(e)
