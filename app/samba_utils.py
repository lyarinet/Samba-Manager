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
    try:
        # Backup original config
        if os.path.exists(SMB_CONF):
            with open(f"{SMB_CONF}.bak", 'w') as f_bak:
                with open(SMB_CONF, 'r') as f_orig:
                    f_bak.write(f_orig.read())
        
        # Check if file exists, if not create it with default template
        if not os.path.exists(SMB_CONF):
            with open(SMB_CONF, 'w') as f:
                f.write(f"""[global]
   server string = {settings.get('server string', 'Samba Server')}
   workgroup = {settings.get('workgroup', 'WORKGROUP')}
   log level = {settings.get('log level', '1')}
   security = user
   passdb backend = tdbsam
   map to guest = bad user
   dns proxy = no
   usershare allow guests = yes
   include = {SHARE_CONF}

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
""")
            return restart_samba_service()
        
        # Update existing file
        with open(SMB_CONF, 'r') as f:
            data = f.read()
        
        # Update settings
        for key, val in settings.items():
            data = re.sub(rf'{key}\s*=.*', f'{key} = {val}', data)
        
        # Ensure include directive exists
        if 'include' not in data:
            data = data.replace('[global]', f'[global]\n   include = {SHARE_CONF}')
        else:
            data = re.sub(r'include\s*=.*', f'include = {SHARE_CONF}', data)
        
        # Write updated config
        with open(SMB_CONF, 'w') as f:
            f.write(data)
        
        # Restart Samba service
        return restart_samba_service()
    except Exception as e:
        print("Error:", e)
        return False

def parse_share_section(content):
    """Parse share sections from a Samba configuration file content"""
    shares = []
    lines = content.split('\n')
    
    current_share = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue
            
        # Check for share section
        if line.startswith('[') and line.endswith(']') and not line == '[global]' and not line == '[printers]' and not line == '[print$]':
            if current_share:
                shares.append(current_share)
            share_name = line[1:-1]
            current_share = {'name': share_name}
        # Check for parameters within a share
        elif current_share and '=' in line:
            key, value = [x.strip() for x in line.split('=', 1)]
            current_share[key] = value
            
    # Add the last share if exists
    if current_share:
        shares.append(current_share)
        
    return shares

def load_shares():
    """Load shares from both development and actual Samba configuration files"""
    shares = []
    
    # Load shares from development file if in DEV_MODE
    if DEV_MODE and os.path.exists(SHARE_CONF):
        try:
            with open(SHARE_CONF, 'r') as f:
                content = f.read()
            shares.extend(parse_share_section(content))
        except Exception as e:
            print(f"Error loading development shares: {e}")
    
    # Always try to load shares from the actual Samba configuration
    if os.path.exists(ACTUAL_SMB_CONF):
        try:
            with open(ACTUAL_SMB_CONF, 'r') as f:
                content = f.read()
            # Add shares from actual Samba config
            actual_shares = parse_share_section(content)
            
            # Merge with existing shares, avoiding duplicates
            share_names = [s['name'] for s in shares]
            for share in actual_shares:
                if share['name'] not in share_names and share['name'] not in ['printers', 'print$']:
                    shares.append(share)
                    share_names.append(share['name'])
        except Exception as e:
            print(f"Error loading actual Samba shares: {e}")
    
    # Create empty shares file if it doesn't exist in DEV_MODE
    if DEV_MODE and not os.path.exists(SHARE_CONF):
        try:
            with open(SHARE_CONF, 'w') as f:
                f.write("# Samba shares configuration\n")
        except Exception as e:
            print(f"Error creating shares file: {e}")
    
    return shares

def save_shares(shares):
    try:
        # Backup original shares file
        if os.path.exists(SHARE_CONF):
            with open(f"{SHARE_CONF}.bak", 'w') as f_bak:
                with open(SHARE_CONF, 'r') as f_orig:
                    f_bak.write(f_orig.read())
        
        # Write new shares configuration
        with open(SHARE_CONF, 'w') as f:
            f.write("# Samba shares configuration\n\n")
            for s in shares:
                f.write(f"[{s['name']}]\n")
                for key in s:
                    if key != 'name':
                        f.write(f"   {key} = {s[key]}\n")
                f.write('\n')
        
        # Restart Samba service
        return restart_samba_service()
    except Exception as e:
        print(f"Error saving shares: {e}")
        return False

def add_or_update_share(new_share):
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
        success, _ = run_command(['id', username])
        
        # Create system user if requested and doesn't exist
        if not success and create_system_user:
            success, _ = run_command(['sudo', 'useradd', '-m', '-s', '/bin/bash', username])
            if not success:
                return False
                
            # Set system password
            success, _ = run_command(['sudo', 'chpasswd'], f"{username}:{password}")
            if not success:
                return False
        
        # Create smbusers group if it doesn't exist
        try:
            grp.getgrnam('smbusers')
        except KeyError:
            run_command(['sudo', 'groupadd', 'smbusers'])
        
        # Add user to smbusers group
        run_command(['sudo', 'usermod', '-aG', 'smbusers', username])
        
        # Add Samba user
        success, _ = run_command(['sudo', 'smbpasswd', '-s', '-a', username], f"{password}\n{password}\n")
        if not success:
            return False
            
        # Enable the Samba user
        success, _ = run_command(['sudo', 'smbpasswd', '-e', username])
        return success
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
