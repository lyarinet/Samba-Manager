import os
import re
import subprocess
import shlex
import grp
import pwd
from pathlib import Path

# Use local configuration files for development
DEV_MODE = os.environ.get('SAMBA_MANAGER_DEV_MODE', '0') == '1'  # Set by environment variable

if DEV_MODE:
    SMB_CONF = './smb.conf'
    SHARE_CONF = './shares.conf'
    ACTUAL_SMB_CONF = '/etc/samba/smb.conf'  # Actual Samba config file
else:
    SMB_CONF = '/etc/samba/smb.conf'
    SHARE_CONF = '/etc/samba/shares.conf'
    ACTUAL_SMB_CONF = SMB_CONF

def parse_share_section(content):
    """Parse share sections from a Samba configuration file content"""
    shares = []
    lines = content.split('\n')
    
    print(f"Parsing content with {len(lines)} lines")
    
    current_share = None
    for line_num, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue
            
        # Check for share section
        if line.startswith('[') and line.endswith(']') and not line == '[global]' and not line == '[printers]' and not line == '[print$]':
            if current_share:
                shares.append(current_share)
                print(f"Added share: {current_share['name']}")
            share_name = line[1:-1]
            print(f"Found share section at line {line_num+1}: {share_name}")
            current_share = {'name': share_name}
        # Check for parameters within a share
        elif current_share and '=' in line:
            key, value = [x.strip() for x in line.split('=', 1)]
            current_share[key] = value
            print(f"  Parameter: {key} = {value}")
            
    # Add the last share if exists
    if current_share:
        shares.append(current_share)
        print(f"Added final share: {current_share['name']}")
        
    print(f"Parsed {len(shares)} shares from content")
    return shares

def parse_config_content(content):
    """Parse Samba configuration content into sections"""
    sections = {}
    current_section = None
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#') or line.startswith(';'):
            continue
        
        # Check for section headers
        if line.startswith('[') and line.endswith(']'):
            section_name = line[1:-1].strip()
            current_section = {}
            sections[section_name] = current_section
        
        # Check for parameters
        elif '=' in line and current_section is not None:
            parts = line.split('=', 1)
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
        '/srv/samba',
        '/var/www',
        '/var/lib/samba/shares',
        '/home/shares',
        '/media',
        '/mnt',
        os.path.expanduser('~/samba_manager')
    ]
    
    # Check existing shares in Samba config
    if os.path.exists(ACTUAL_SMB_CONF):
        try:
            with open(ACTUAL_SMB_CONF, 'r') as f:
                content = f.read()
            
            # Extract share sections and their paths
            shares = parse_share_section(content)
            for share in shares:
                if 'name' in share and 'path' in share:
                    if os.path.exists(share['path']):
                        share_dirs[share['name']] = share['path']
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
                    if os.path.isdir(full_path) and not item.startswith('.'):
                        if item not in share_dirs:
                            share_dirs[item] = full_path
            except Exception as e:
                print(f"Error checking location {location}: {e}")
    
    # Add some default shares if none found
    if not share_dirs:
        share_dirs = {
            'public': '/srv/samba/public',
            'share': os.path.expanduser('~/samba_manager')
        }
    
    return share_dirs

# Get auto-detected share directories
SHARE_DIRS = detect_share_directories()

def check_sudo_access():
    """Check if the application has sudo access to manage Samba"""
    if DEV_MODE:
        return True  # In development mode, we don't need sudo
    try:
        result = subprocess.run(['sudo', '-n', 'true'], capture_output=True)
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
                check=True
            )
        else:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except Exception as e:
        return False, str(e)

def restart_samba_service():
    """Restart the Samba service to apply configuration changes"""
    if DEV_MODE:
        print("[DEV MODE] Would restart Samba service in production")
        return True
    try:
        subprocess.run(['sudo', 'systemctl', 'restart', 'smbd'], check=True)
        subprocess.run(['sudo', 'systemctl', 'restart', 'nmbd'], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def get_samba_status():
    """Get the status of the Samba service"""
    if DEV_MODE:
        return {'smbd': 'active (dev)', 'nmbd': 'active (dev)'}
    try:
        smbd = subprocess.run(['systemctl', 'is-active', 'smbd'], capture_output=True, text=True)
        nmbd = subprocess.run(['systemctl', 'is-active', 'nmbd'], capture_output=True, text=True)
        return {
            'smbd': smbd.stdout.strip(),
            'nmbd': nmbd.stdout.strip()
        }
    except Exception:
        return {'smbd': 'unknown', 'nmbd': 'unknown'}

def read_global_settings():
    try:
        with open(SMB_CONF, 'r') as f:
            data = f.read()
        return {
            'server_string': re.search(r'server string\s*=\s*(.*)', data).group(1),
            'workgroup': re.search(r'workgroup\s*=\s*(.*)', data).group(1),
            'log_level': re.search(r'log level\s*=\s*(.*)', data).group(1),
        }
    except Exception as e:
        return {'error': str(e), 'server_string': 'Samba Server', 'workgroup': 'WORKGROUP', 'log_level': '1'}

def write_global_settings(settings):
    """Write global settings to the Samba configuration file"""
    try:
        # Get the current configuration
        config_content = read_samba_config()
        
        # Create a backup of the current config
        backup_path = '/etc/samba/smb.conf.bak'
        with open(backup_path, 'w') as f:
            f.write(config_content)
        
        # Parse the configuration into sections
        sections = parse_config_content(config_content)
        
        # Update the global section
        if 'global' in sections:
            global_section = sections['global']
            
            # Update the settings
            for key, value in settings.items():
                if value:  # Only update if value is not empty
                    global_section[key] = value
        else:
            # Create a new global section if it doesn't exist
            sections['global'] = settings
        
        # Convert the sections back to a configuration string
        new_config = ''
        for section_name, section_params in sections.items():
            new_config += f'[{section_name}]\n'
            for param_name, param_value in section_params.items():
                new_config += f'    {param_name} = {param_value}\n'
            new_config += '\n'
        
        # Write the configuration to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(new_config)
            temp_path = temp_file.name
        
        # Copy the temporary file to the Samba configuration file using sudo
        result = subprocess.run(['sudo', 'cp', temp_path, '/etc/samba/smb.conf'], 
                              capture_output=True, text=True, check=False)
        
        # Clean up the temporary file
        os.unlink(temp_path)
        
        if result.returncode != 0:
            print(f"Error writing config: {result.stderr}")
            return False
        
        # Validate the configuration
        validate_cmd = subprocess.run(['sudo', 'testparm', '-s', '/etc/samba/smb.conf'], 
                                     capture_output=True, text=True, check=False)
        
        if validate_cmd.returncode != 0:
            # If validation fails, restore the backup
            subprocess.run(['sudo', 'cp', backup_path, '/etc/samba/smb.conf'], check=False)
            print(f"Invalid configuration: {validate_cmd.stderr}")
            return False
        
        # Restart Samba services
        restart_cmd = subprocess.run(['sudo', 'systemctl', 'restart', 'smbd', 'nmbd'], 
                                    capture_output=True, text=True, check=False)
        
        if restart_cmd.returncode != 0:
            print(f"Error restarting services: {restart_cmd.stderr}")
            return False
        
        return True
    
    except Exception as e:
        print(f"Exception in write_global_settings: {str(e)}")
        return False

def load_shares():
    """Load shares from both development and actual Samba configuration files"""
    shares = []
    
    print(f"Loading shares. DEV_MODE={DEV_MODE}, SHARE_CONF={SHARE_CONF}, ACTUAL_SMB_CONF={ACTUAL_SMB_CONF}")
    
    # Load shares from development file if in DEV_MODE
    if DEV_MODE and os.path.exists(SHARE_CONF):
        try:
            print(f"Loading shares from development file: {SHARE_CONF}")
            with open(SHARE_CONF, 'r') as f:
                content = f.read()
            dev_shares = parse_share_section(content)
            shares.extend(dev_shares)
            print(f"Loaded {len(dev_shares)} shares from development file")
        except Exception as e:
            print(f"Error loading development shares: {e}")
    
    # Always try to load shares from the actual Samba configuration
    if os.path.exists(ACTUAL_SMB_CONF):
        try:
            print(f"Loading shares from actual Samba config: {ACTUAL_SMB_CONF}")
            # Use sudo to read the file
            result = subprocess.run(['sudo', 'cat', ACTUAL_SMB_CONF], capture_output=True, text=True, check=True)
            content = result.stdout
            print(f"Read {len(content)} bytes from main config file")
            
            # Check if the file includes the shares.conf
            include_match = re.search(r'include\s*=\s*(\S+)', content)
            if include_match:
                shares_file = include_match.group(1)
                print(f"Found include directive for: {shares_file}")
                
                # Read the shares file directly
                if os.path.exists(shares_file):
                    try:
                        print(f"Reading shares file: {shares_file}")
                        shares_result = subprocess.run(['sudo', 'cat', shares_file], capture_output=True, text=True, check=True)
                        shares_content = shares_result.stdout
                        print(f"Read {len(shares_content)} bytes from shares file")
                        
                        # Parse shares from the shares file
                        shares_from_file = parse_share_section(shares_content)
                        print(f"Found {len(shares_from_file)} shares in shares file")
                        shares.extend(shares_from_file)
                    except Exception as e:
                        print(f"Error reading shares file: {e}")
            
            # Also parse the main config file for any shares defined there
            actual_shares = parse_share_section(content)
            print(f"Found {len(actual_shares)} shares in actual Samba config")
            
            # Merge with existing shares, avoiding duplicates
            share_names = [s['name'] for s in shares]
            added_count = 0
            for share in actual_shares:
                if share['name'] not in share_names and share['name'] not in ['printers', 'print$']:
                    shares.append(share)
                    share_names.append(share['name'])
                    added_count += 1
            print(f"Added {added_count} unique shares from actual Samba config")
        except Exception as e:
            print(f"Error loading actual Samba shares: {e}")
    else:
        print(f"Actual Samba config file not found: {ACTUAL_SMB_CONF}")
    
    # Create empty shares file if it doesn't exist in DEV_MODE
    if DEV_MODE and not os.path.exists(SHARE_CONF):
        try:
            print(f"Creating empty shares file: {SHARE_CONF}")
            with open(SHARE_CONF, 'w') as f:
                f.write("# Samba shares configuration\n")
        except Exception as e:
            print(f"Error creating shares file: {e}")
    
    print(f"Total shares loaded: {len(shares)}")
    return shares

def save_shares(shares):
    try:
        print(f"Saving {len(shares)} shares to {SHARE_CONF}")
        
        # Create temporary file with new configuration
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("# Samba shares configuration\n\n")
            for s in shares:
                temp_file.write(f"[{s['name']}]\n")
                for key in s:
                    if key != 'name':
                        temp_file.write(f"   {key} = {s[key]}\n")
                temp_file.write('\n')
            temp_path = temp_file.name
            print(f"Created temporary file at {temp_path}")
        
        # Backup original shares file if it exists
        if os.path.exists(SHARE_CONF):
            try:
                subprocess.run(['sudo', 'cp', SHARE_CONF, f"{SHARE_CONF}.bak"], check=True)
                print(f"Backed up {SHARE_CONF} to {SHARE_CONF}.bak")
            except Exception as e:
                print(f"Warning: Could not backup shares file: {e}")
        
        # Use sudo to copy the temporary file to the correct location
        try:
            print(f"Copying temporary file to {SHARE_CONF}")
            subprocess.run(['sudo', 'cp', temp_path, SHARE_CONF], check=True)
            os.unlink(temp_path)  # Remove the temp file
            print(f"Successfully copied configuration to {SHARE_CONF}")
        except Exception as e:
            print(f"Error copying shares file: {e}")
            return False
        
        # Ensure the include directive exists in the main config
        try:
            if os.path.exists(SMB_CONF):
                print(f"Checking for include directive in {SMB_CONF}")
                with open(SMB_CONF, 'r') as f:
                    content = f.read()
                
                if f"include = {SHARE_CONF}" not in content:
                    print(f"Adding include directive to {SMB_CONF}")
                    # Create a temporary file with updated content
                    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                        if '[global]' in content:
                            new_content = content.replace('[global]', f'[global]\n   include = {SHARE_CONF}')
                        else:
                            new_content = f"[global]\n   include = {SHARE_CONF}\n\n{content}"
                        temp_file.write(new_content)
                        temp_path = temp_file.name
                    
                    # Use sudo to copy the temporary file to the correct location
                    subprocess.run(['sudo', 'cp', temp_path, SMB_CONF], check=True)
                    os.unlink(temp_path)  # Remove the temp file
                    print(f"Added include directive to {SMB_CONF}")
        except Exception as e:
            print(f"Warning: Could not update include directive: {e}")
        
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
    shares = load_shares()
    for idx, s in enumerate(shares):
        if s['name'] == new_share['name']:
            shares[idx] = new_share
            break
    else:
        shares.append(new_share)
    
    # Ensure the share directory exists with proper permissions
    create_share_directory(new_share['name'], new_share['path'])
    
    return save_shares(shares)

def delete_share(name):
    shares = [s for s in load_shares() if s['name'] != name]
    return save_shares(shares)

def list_system_users():
    try:
        output = subprocess.check_output(['getent', 'passwd']).decode()
        return [line.split(':')[0] for line in output.strip().split('\n') if int(line.split(':')[2]) >= 1000]
    except Exception:
        return []

def list_system_groups():
    try:
        output = subprocess.check_output(['getent', 'group']).decode()
        return [line.split(':')[0] for line in output.strip().split('\n') if int(line.split(':')[2]) >= 1000]
    except Exception:
        return []

def validate_share_path(path):
    """Validate if a share path exists and is accessible by Samba"""
    if not os.path.exists(path):
        return False, "Path does not exist"
    
    # Check if path is readable
    if not os.access(path, os.R_OK):
        return False, "Path is not readable"
    
    return True, "Path is valid"

def export_config():
    try:
        with open(SMB_CONF, 'r') as f1, open(SHARE_CONF, 'r') as f2:
            return f1.read() + '\n' + f2.read()
    except Exception as e:
        return f"Error exporting configuration: {str(e)}"

def import_config(data):
    try:
        parts = data.split('[global]')
        if len(parts) >= 2:
            global_conf = '[global]' + parts[1].split('[', 1)[0]
            rest = '[' + parts[1].split('[', 1)[1]
            
            # Backup original files
            if os.path.exists(SMB_CONF):
                with open(f"{SMB_CONF}.bak", 'w') as f_bak:
                    with open(SMB_CONF, 'r') as f_orig:
                        f_bak.write(f_orig.read())
            
            if os.path.exists(SHARE_CONF):
                with open(f"{SHARE_CONF}.bak", 'w') as f_bak:
                    with open(SHARE_CONF, 'r') as f_orig:
                        f_bak.write(f_orig.read())
            
            # Write new configuration
            with open(SMB_CONF, 'w') as f1:
                f1.write(global_conf.strip() + '\n')
            with open(SHARE_CONF, 'w') as f2:
                f2.write(rest.strip() + '\n')
            
            # Restart Samba service
            return restart_samba_service()
        return False
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
            success, output = run_command(['pdbedit', '-L'])
            if success and output.strip():
                users = []
                for line in output.strip().split('\n'):
                    if line.strip():
                        parts = line.split(':')
                        if len(parts) >= 1:
                            username = parts[0].strip()
                            users.append({
                                'username': username,
                                'enabled': True,  # Assume enabled by default
                                'flags': 'U'
                            })
                return users
                
            # Try smbpasswd -s command
            success, output = run_command(['cat', '/etc/samba/smbpasswd'])
            if success and output.strip():
                users = []
                for line in output.strip().split('\n'):
                    if line.strip() and not line.startswith('#'):
                        parts = line.split(':')
                        if len(parts) >= 1:
                            username = parts[0].strip()
                            users.append({
                                'username': username,
                                'enabled': True,
                                'flags': 'U'
                            })
                return users
                
            # Return mock data if all else fails
            return [
                {'username': 'user1', 'enabled': True, 'flags': 'U'},
                {'username': 'user2', 'enabled': False, 'flags': 'UD'}
            ]
        except Exception:
            # Return mock data if there's an error
            return [
                {'username': 'user1', 'enabled': True, 'flags': 'U'},
                {'username': 'user2', 'enabled': False, 'flags': 'UD'}
            ]
    
    try:
        # First try pdbedit with sudo
        success, output = run_command(['sudo', 'pdbedit', '-L'])
        if success and output.strip():
            users = []
            for line in output.strip().split('\n'):
                if line.strip():
                    parts = line.split(':')
                    if len(parts) >= 1:
                        username = parts[0].strip()
                        # Get detailed info for this user
                        detail_success, detail_output = run_command(['sudo', 'pdbedit', '-v', '-u', username])
                        enabled = True
                        flags = 'U'
                        if detail_success:
                            for detail_line in detail_output.split('\n'):
                                if 'Account Flags:' in detail_line:
                                    flags = detail_line.split(':', 1)[1].strip()
                                    enabled = 'D' not in flags
                        users.append({
                            'username': username,
                            'enabled': enabled,
                            'flags': flags
                        })
            return users
        
        # If pdbedit fails, try reading smbpasswd file directly
        success, output = run_command(['sudo', 'cat', '/etc/samba/smbpasswd'])
        if success and output.strip():
            users = []
            for line in output.strip().split('\n'):
                if line.strip() and not line.startswith('#'):
                    parts = line.split(':')
                    if len(parts) >= 1:
                        username = parts[0].strip()
                        # Check if user is disabled (has 'D' flag)
                        disabled = len(parts) > 4 and 'D' in parts[4]
                        users.append({
                            'username': username,
                            'enabled': not disabled,
                            'flags': parts[4] if len(parts) > 4 else 'U'
                        })
            return users
            
        # If all else fails, try to get system users that might be Samba users
        system_users = list_system_users()
        return [{'username': user, 'enabled': True, 'flags': 'U'} for user in system_users]
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
        check_user = subprocess.run(['id', username], capture_output=True, text=True, check=False)
        user_exists = check_user.returncode == 0
        
        # Create system user if requested and doesn't exist
        if not user_exists and create_system_user:
            print(f"Creating system user: {username}")
            create_user = subprocess.run(['sudo', 'useradd', '-m', '-s', '/bin/bash', username], 
                                        capture_output=True, text=True, check=False)
            if create_user.returncode != 0:
                print(f"Failed to create system user: {create_user.stderr}")
                return False
                
            # Set system password
            set_pass = subprocess.Popen(['sudo', 'chpasswd'], 
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       text=True)
            stdout, stderr = set_pass.communicate(input=f"{username}:{password}")
            if set_pass.returncode != 0:
                print(f"Failed to set system password: {stderr}")
                return False
        
        # Create smbusers group if it doesn't exist
        check_group = subprocess.run(['getent', 'group', 'smbusers'], 
                                    capture_output=True, text=True, check=False)
        if check_group.returncode != 0:
            print("Creating smbusers group")
            create_group = subprocess.run(['sudo', 'groupadd', 'smbusers'], 
                                        capture_output=True, text=True, check=False)
            if create_group.returncode != 0:
                print(f"Failed to create smbusers group: {create_group.stderr}")
        
        # If the user exists, add them to smbusers group
        if user_exists or create_system_user:
            print(f"Adding {username} to smbusers group")
            add_to_group = subprocess.run(['sudo', 'usermod', '-aG', 'smbusers', username], 
                                        capture_output=True, text=True, check=False)
            if add_to_group.returncode != 0:
                print(f"Failed to add user to smbusers group: {add_to_group.stderr}")
        
        # Add Samba user
        print(f"Creating Samba user: {username}")
        process = subprocess.Popen(['sudo', 'smbpasswd', '-s', '-a', username],
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True)
        
        stdout, stderr = process.communicate(input=f"{password}\n{password}\n")
        
        if process.returncode != 0:
            print(f"Failed to create Samba user: {stderr}")
            return False
        
        # Enable the Samba user
        print("Enabling Samba user")
        enable = subprocess.run(['sudo', 'smbpasswd', '-e', username], 
                               capture_output=True, text=True, check=False)
        
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
        success, _ = run_command(['sudo', 'smbpasswd', '-x', username])
        
        # Delete system user if requested
        if delete_system_user:
            run_command(['sudo', 'userdel', '-r', username])
            
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
        success, _ = run_command(['sudo', 'smbpasswd', '-e', username])
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
        success, _ = run_command(['sudo', 'smbpasswd', '-d', username])
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
        success, _ = run_command(['sudo', 'smbpasswd', '-s', username], f"{password}\n{password}\n")
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
        success, _ = run_command(['which', 'smbd'])
        if success:
            return True
            
        # Install Samba
        success, _ = run_command(['sudo', 'apt-get', 'update'])
        if not success:
            return False
            
        success, _ = run_command(['sudo', 'apt-get', 'install', '-y', 'samba', 'samba-common-bin'])
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
        # Create the directory
        run_command(['sudo', 'mkdir', '-p', path])
        
        # Create smbusers group if it doesn't exist
        try:
            grp.getgrnam('smbusers')
        except KeyError:
            run_command(['sudo', 'groupadd', 'smbusers'])
        
        # Set permissions
        run_command(['sudo', 'chown', '-R', 'root:smbusers', path])
        run_command(['sudo', 'chmod', '-R', '2770', path])  # 2 sets the SGID bit
        
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
            grp.getgrnam('smbusers')
        except KeyError:
            run_command(['sudo', 'groupadd', 'smbusers'])
        
        # Get all system users
        users = list_system_users()
        
        # Add each user to the smbusers group
        for user in users:
            run_command(['sudo', 'usermod', '-aG', 'smbusers', user])
            
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
            grp.getgrnam('smbusers')
        except KeyError:
            run_command(['sudo', 'groupadd', 'smbusers'])
        
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
            grp.getgrnam('smbusers')
        except KeyError:
            run_command(['sudo', 'groupadd', 'smbusers'])
        
        # Add users to smbusers group
        add_users_to_smbusers_group()
        
        # Auto-detect share directories
        share_directories = detect_share_directories()
        
        # Create share directories
        for name, path in share_directories.items():
            create_share_directory(name, path)
        
        # Configure global settings
        write_global_settings({
            'server string': 'Samba Server',
            'workgroup': 'WORKGROUP',
            'log level': '1'
        })
        
        # Create shares based on auto-detected directories
        for name, path in share_directories.items():
            add_or_update_share({
                'name': name,
                'path': path,
                'read only': 'no',
                'valid users': '@smbusers',
                'guest ok': 'no',
                'browseable': 'yes',
                'create mask': '0770',
                'directory mask': '0770',
                'force group': 'smbusers',
                'force user': 'root'
            })
        
        # Enable and restart Samba services
        run_command(['sudo', 'systemctl', 'enable', 'smbd'])
        run_command(['sudo', 'systemctl', 'enable', 'nmbd'])
        restart_samba_service()
        
        return True
    except Exception as e:
        print(f"Error setting up Samba: {e}")
        return False

def get_samba_installation_status():
    """Get the status of the Samba installation"""
    status = {
        'installed': False,
        'running': False,
        'configured': False,
        'shares': [],
        'users': []
    }
    
    try:
        # Check if Samba is installed
        success, _ = run_command(['which', 'smbd'])
        status['installed'] = success
        
        if not success:
            return status
            
        # Check if Samba is running
        samba_status = get_samba_status()
        status['running'] = samba_status['smbd'] == 'active'
        
        # Check if Samba is configured
        status['configured'] = os.path.exists(ACTUAL_SMB_CONF)
        
        # Get shares
        status['shares'] = load_shares()
        
        # Get users
        status['users'] = get_samba_users()
        
        return status
    except Exception as e:
        print(f"Error getting Samba installation status: {e}")
        return status
