import os
import re
import subprocess

# Use local configuration files for development
DEV_MODE = True  # Set to False in production

if DEV_MODE:
    SMB_CONF = './smb.conf'
    SHARE_CONF = './shares.conf'
    ACTUAL_SMB_CONF = '/etc/samba/smb.conf'  # Actual Samba config file
else:
    SMB_CONF = '/etc/samba/smb.conf'
    SHARE_CONF = '/etc/samba/shares.conf'
    ACTUAL_SMB_CONF = SMB_CONF

def check_sudo_access():
    """Check if the application has sudo access to manage Samba"""
    if DEV_MODE:
        return True  # In development mode, we don't need sudo
    try:
        result = subprocess.run(['sudo', '-n', 'true'], capture_output=True)
        return result.returncode == 0
    except Exception:
        return False

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
   include = {SHARE_CONF}
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
