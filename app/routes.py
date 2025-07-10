from flask import Blueprint, render_template, request, redirect, flash, send_file, url_for, jsonify
from flask_login import login_required, current_user
import io
import os
import subprocess
import tempfile
import datetime
from .samba_utils import *

bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def index():
    # Get Samba service status
    status = get_samba_status()
    has_sudo = check_sudo_access()
    
    # Get Samba installation status
    installation_status = get_samba_installation_status()
    
    # Add datetime for the template
    now = datetime.datetime.now()
    
    return render_template('index.html', status=status, has_sudo=has_sudo, installation_status=installation_status, now=now)

@bp.route('/global-settings', methods=['GET', 'POST'])
@login_required
def global_settings():
    if request.method == 'POST':
        if not check_sudo_access():
            flash('Error: Sudo access is required to modify Samba settings', 'error')
            return redirect('/global-settings')
            
        result = write_global_settings({
            'server string': request.form['server_string'],
            'workgroup': request.form['workgroup'],
            'log level': request.form['log_level']
        })
        
        if result:
            flash('Settings saved and Samba service restarted', 'success')
        else:
            flash('Failed to save settings. Check logs for details', 'error')
            
        return redirect('/global-settings')
        
    global_settings = read_global_settings()
    has_sudo = check_sudo_access()
    
    # Get Samba service status
    status = get_samba_status()
    
    return render_template('global_settings.html', 
                          global_settings=global_settings, 
                          status=status,
                          has_sudo=has_sudo)

@bp.route('/shares', methods=['GET', 'POST'])
@login_required
def shares():
    has_sudo = check_sudo_access()
    all_shares = load_shares()
    
    # Debug logging
    print(f"Loaded {len(all_shares)} shares from configuration")
    for share in all_shares:
        print(f"Share: {share.get('name', 'unknown')} - Path: {share.get('path', 'unknown')}")
    
    # Sort shares: system shares first, then local shares
    system_shares = [s for s in all_shares if s['name'] in ['secure-share', 'share']]
    local_shares = [s for s in all_shares if s['name'] not in ['secure-share', 'share']]
    sorted_shares = system_shares + local_shares
    
    print(f"Sending {len(sorted_shares)} shares to template")
    
    return render_template('shares.html', 
                          shares=sorted_shares, 
                          users=list_system_users(), 
                          groups=list_system_groups(),
                          has_sudo=has_sudo)

@bp.route('/add-share', methods=['POST'])
@login_required
def add_share():
    has_sudo = check_sudo_access()
    if not has_sudo:
        flash('Error: Sudo access is required to add shares', 'error')
        return redirect('/shares')
    
    name = request.form['name']
    path = request.form['path']
    
    # Validate path
    valid, message = validate_share_path(path)
    if not valid and not os.path.exists(path):
        # Try to create the directory
        try:
            # Use sudo to create the directory
            subprocess.run(['sudo', 'mkdir', '-p', path], check=True)
            valid = os.path.exists(path)
            if valid:
                message = "Path created successfully"
        except Exception as e:
            message = f"Failed to create path: {str(e)}"
    
    if not valid:
        flash(f'Invalid path: {message}', 'error')
        return redirect('/shares')
    
    # Check if share name already exists
    all_shares = load_shares()
    if any(s['name'] == name for s in all_shares):
        flash(f'A share with the name "{name}" already exists', 'error')
        return redirect('/shares')
    
    # Check if it's trying to override a system share
    if name in ['secure-share', 'share']:
        flash(f'Cannot create system share "{name}". Edit /etc/samba/smb.conf directly.', 'error')
        return redirect('/shares')
    
    # Create new share
    share = {
        'name': name,
        'path': path,
        'comment': request.form.get('comment', ''),
        'browseable': 'yes' if request.form.get('browseable') else 'no',
        'read only': 'yes' if request.form.get('read_only') else 'no',
        'guest ok': 'yes' if request.form.get('guest_ok') else 'no',
        'valid users': request.form.get('valid_users', ''),
        'write list': request.form.get('write_list', ''),
        'create mask': request.form.get('create_mask', '0744'),
        'directory mask': request.form.get('directory_mask', '0755'),
        'force group': 'smbusers'
    }
    
    result = add_or_update_share(share)
    if result:
        flash('Share added successfully and Samba service restarted', 'success')
    else:
        flash('Failed to add share', 'error')
    
    return redirect('/shares')

@bp.route('/edit-share', methods=['POST'])
@login_required
def edit_share():
    has_sudo = check_sudo_access()
    if not has_sudo:
        flash('Error: Sudo access is required to modify shares', 'error')
        return redirect('/shares')
    
    original_name = request.form['original_name']
    name = request.form['name']
    path = request.form['path']
    
    # Check if it's a system share
    if original_name in ['secure-share', 'share']:
        flash(f'Cannot modify system share "{original_name}". Edit /etc/samba/smb.conf directly.', 'error')
        return redirect('/shares')
    
    # Validate path
    valid, message = validate_share_path(path)
    if not valid and not os.path.exists(path):
        # Try to create the directory
        try:
            # Use sudo to create the directory
            subprocess.run(['sudo', 'mkdir', '-p', path], check=True)
            valid = os.path.exists(path)
            if valid:
                message = "Path created successfully"
        except Exception as e:
            message = f"Failed to create path: {str(e)}"
    
    if not valid:
        flash(f'Invalid path: {message}', 'error')
        return redirect('/shares')
    
    # Check if new name already exists (if name was changed)
    if original_name != name:
        all_shares = load_shares()
        if any(s['name'] == name for s in all_shares):
            flash(f'A share with the name "{name}" already exists', 'error')
            return redirect('/shares')
    
    # Update share
    share = {
        'name': name,
        'path': path,
        'comment': request.form.get('comment', ''),
        'browseable': 'yes' if request.form.get('browseable') else 'no',
        'read only': 'yes' if request.form.get('read_only') else 'no',
        'guest ok': 'yes' if request.form.get('guest_ok') else 'no',
        'valid users': request.form.get('valid_users', ''),
        'write list': request.form.get('write_list', ''),
        'create mask': request.form.get('create_mask', '0744'),
        'directory mask': request.form.get('directory_mask', '0755')
    }
    
    # If name was changed, delete the old share first
    if original_name != name:
        delete_share(original_name)
    
    result = add_or_update_share(share)
    if result:
        flash('Share updated successfully and Samba service restarted', 'success')
    else:
        flash('Failed to update share', 'error')
    
    return redirect('/shares')

@bp.route('/delete-share', methods=['POST'])
@login_required
def delete_share_route():
    has_sudo = check_sudo_access()
    if not has_sudo:
        flash('Error: Sudo access is required to delete shares', 'error')
        return redirect('/shares')
    
    share_name = request.form['name']
    
    # Check if it's a system share
    if share_name in ['secure-share', 'share']:
        flash(f'Cannot delete system share "{share_name}". Edit /etc/samba/smb.conf directly.', 'error')
        return redirect('/shares')
    
    result = delete_share(share_name)
    if result:
        flash('Share deleted successfully and Samba service restarted', 'success')
    else:
        flash('Failed to delete share', 'error')
    
    return redirect('/shares')

@bp.route('/users', methods=['GET'])
@login_required
def users():
    if not check_sudo_access():
        flash('Error: Sudo access is required to manage Samba users', 'error')
        return redirect('/')
        
    users = get_samba_users()
    system_users = list_system_users()
    system_groups = list_system_groups()
    
    return render_template('users.html', 
                          users=users, 
                          system_users=system_users,
                          groups=system_groups,
                          has_sudo=check_sudo_access())

@bp.route('/users/add', methods=['POST'])
@login_required
def add_user():
    if not check_sudo_access():
        flash('Error: Sudo access is required to manage Samba users', 'error')
        return redirect('/users')
        
    username = request.form.get('username')
    password = request.form.get('password')
    create_system_user = request.form.get('create_system_user') == 'on'
    
    if not username or not password:
        flash('Username and password are required', 'error')
        return redirect('/users')
        
    result = add_samba_user(username, password, create_system_user)
    
    if result:
        flash(f'User {username} added successfully', 'success')
    else:
        flash(f'Failed to add user {username}', 'error')
        
    return redirect('/users')

@bp.route('/users/delete/<username>', methods=['POST'])
@login_required
def delete_user(username):
    if not check_sudo_access():
        flash('Error: Sudo access is required to manage Samba users', 'error')
        return redirect('/users')
        
    delete_system_user = request.form.get('delete_system_user') == 'on'
    
    result = remove_samba_user(username, delete_system_user)
    
    if result:
        flash(f'User {username} deleted successfully', 'success')
    else:
        flash(f'Failed to delete user {username}', 'error')
        
    return redirect('/users')

@bp.route('/users/enable/<username>', methods=['POST'])
@login_required
def enable_user(username):
    if not check_sudo_access():
        flash('Error: Sudo access is required to manage Samba users', 'error')
        return redirect('/users')
        
    result = enable_samba_user(username)
    
    if result:
        flash(f'User {username} enabled successfully', 'success')
    else:
        flash(f'Failed to enable user {username}', 'error')
        
    return redirect('/users')

@bp.route('/users/disable/<username>', methods=['POST'])
@login_required
def disable_user(username):
    if not check_sudo_access():
        flash('Error: Sudo access is required to manage Samba users', 'error')
        return redirect('/users')
        
    result = disable_samba_user(username)
    
    if result:
        flash(f'User {username} disabled successfully', 'success')
    else:
        flash(f'Failed to disable user {username}', 'error')
        
    return redirect('/users')

@bp.route('/users/reset-password/<username>', methods=['POST'])
@login_required
def reset_password(username):
    if not check_sudo_access():
        flash('Error: Sudo access is required to manage Samba users', 'error')
        return redirect('/users')
        
    password = request.form.get('password')
    
    if not password:
        flash('Password is required', 'error')
        return redirect('/users')
        
    result = reset_samba_password(username, password)
    
    if result:
        flash(f'Password for {username} reset successfully', 'success')
    else:
        flash(f'Failed to reset password for {username}', 'error')
        
    return redirect('/users')

@bp.route('/export')
@login_required
def export():
    data = export_config()
    if data.startswith("Error"):
        flash(data, 'error')
        return redirect('/')
    return send_file(io.BytesIO(data.encode()), mimetype='text/plain', as_attachment=True, download_name='smb_backup.conf')

@bp.route('/import', methods=['POST'])
@login_required
def import_conf():
    if not check_sudo_access():
        flash('Error: Sudo access is required to import Samba configuration', 'error')
        return redirect('/')
        
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect('/')
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect('/')
        
    content = file.read().decode()
    result = import_config(content)
    
    if result:
        flash('Configuration imported successfully and Samba service restarted', 'success')
    else:
        flash('Import failed. Check logs for details', 'error')
        
    return redirect('/')

@bp.route('/restart')
@login_required
def restart_service():
    if not check_sudo_access():
        flash('Error: Sudo access is required to restart Samba service', 'error')
        return redirect('/')
        
    result = restart_samba_service()
    
    if result:
        flash('Samba service restarted successfully', 'success')
    else:
        flash('Failed to restart Samba service', 'error')
        
    return redirect('/')

@bp.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    """Setup Samba from the web interface"""
    if not check_sudo_access():
        flash('Error: Sudo access is required to set up Samba', 'error')
        return redirect('/')
    
    if request.method == 'POST':
        result = setup_samba()
        if result:
            flash('Samba has been set up successfully', 'success')
        else:
            flash('Failed to set up Samba. Check logs for details', 'error')
        return redirect('/')
    
    # Get current installation status
    installation_status = get_samba_installation_status()
    
    # Get Samba service status
    status = get_samba_status()
    
    return render_template('setup.html', 
                          installation_status=installation_status,
                          status=status,
                          has_sudo=check_sudo_access())

@bp.route('/fix-permissions', methods=['POST'])
@login_required
def fix_permissions():
    """Fix permissions on share directories"""
    if not check_sudo_access():
        flash('Error: Sudo access is required to fix permissions', 'error')
        return redirect('/')
    
    result = fix_share_permissions()
    if result:
        flash('Share permissions have been fixed successfully', 'success')
    else:
        flash('Failed to fix share permissions. Check logs for details', 'error')
    
    return redirect('/')

@bp.route('/maintenance')
@login_required
def maintenance():
    """Maintenance page for Samba"""
    if not check_sudo_access():
        flash('Error: Sudo access is required to access maintenance functions', 'error')
        return redirect('/')
    
    # Get current installation status
    installation_status = get_samba_installation_status()
    
    # Get Samba service status
    status = get_samba_status()
    
    # Get shares for permission management
    shares = load_shares()
    
    return render_template('maintenance.html', 
                          installation_status=installation_status,
                          status=status,
                          shares=shares,
                          has_sudo=check_sudo_access())

@bp.route('/install-samba', methods=['POST'])
@login_required
def install_samba():
    """Install Samba if not already installed"""
    if not check_sudo_access():
        flash('Error: Sudo access is required to install Samba', 'error')
        return redirect('/')
    
    result = ensure_samba_installed()
    if result:
        flash('Samba has been installed successfully', 'success')
    else:
        flash('Failed to install Samba. Check logs for details', 'error')
    
    return redirect('/maintenance')

@bp.route('/start-service', methods=['POST'])
@login_required
def start_service():
    """Start the Samba service"""
    if not check_sudo_access():
        flash('Error: Sudo access is required to start Samba service', 'error')
        return redirect('/maintenance')
    
    try:
        if DEV_MODE:
            flash('[DEV MODE] Would start Samba service in production', 'info')
            return redirect('/maintenance')
            
        subprocess.run(['sudo', 'systemctl', 'start', 'smbd'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', 'nmbd'], check=True)
        flash('Samba service started successfully', 'success')
    except Exception as e:
        flash(f'Failed to start Samba service: {str(e)}', 'error')
    
    return redirect('/maintenance')

@bp.route('/stop-service', methods=['POST'])
@login_required
def stop_service():
    """Stop the Samba service"""
    if not check_sudo_access():
        flash('Error: Sudo access is required to stop Samba service', 'error')
        return redirect('/maintenance')
    
    try:
        if DEV_MODE:
            flash('[DEV MODE] Would stop Samba service in production', 'info')
            return redirect('/maintenance')
            
        subprocess.run(['sudo', 'systemctl', 'stop', 'smbd'], check=True)
        subprocess.run(['sudo', 'systemctl', 'stop', 'nmbd'], check=True)
        flash('Samba service stopped successfully', 'success')
    except Exception as e:
        flash(f'Failed to stop Samba service: {str(e)}', 'error')
    
    return redirect('/maintenance')

@bp.route('/edit-config', methods=['GET', 'POST'])
@login_required
def edit_config():
    """Edit Samba configuration file directly"""
    if not check_sudo_access():
        flash('Error: Sudo access is required to edit Samba configuration', 'error')
        return redirect('/')
    
    config_file = SMB_CONF
    share_file = SHARE_CONF
    
    if request.method == 'POST':
        if 'main_config' in request.form:
            try:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                    temp_file.write(request.form['main_config'])
                    temp_path = temp_file.name
                
                # Use sudo to move the file to the correct location
                result = subprocess.run(
                    ['sudo', 'cp', temp_path, config_file],
                    capture_output=True, text=True, check=True
                )
                os.unlink(temp_path)  # Remove the temp file
                flash('Main configuration file updated successfully', 'success')
            except subprocess.CalledProcessError as e:
                flash(f'Error updating main configuration: {e.stderr}', 'error')
            except Exception as e:
                flash(f'Error updating main configuration: {str(e)}', 'error')
        
        if 'share_config' in request.form:
            try:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                    temp_file.write(request.form['share_config'])
                    temp_path = temp_file.name
                
                # Use sudo to move the file to the correct location
                result = subprocess.run(
                    ['sudo', 'cp', temp_path, share_file],
                    capture_output=True, text=True, check=True
                )
                os.unlink(temp_path)  # Remove the temp file
                flash('Share configuration file updated successfully', 'success')
            except subprocess.CalledProcessError as e:
                flash(f'Error updating share configuration: {e.stderr}', 'error')
            except Exception as e:
                flash(f'Error updating share configuration: {str(e)}', 'error')
        
        # Restart Samba service after config changes
        if restart_samba_service():
            flash('Samba service restarted successfully', 'success')
        else:
            flash('Failed to restart Samba service', 'error')
        
        return redirect('/edit-config')
    
    # Read configuration files
    main_config = ""
    share_config = ""
    
    try:
        if os.path.exists(config_file):
            result = subprocess.run(
                ['sudo', 'cat', config_file],
                capture_output=True, text=True, check=True
            )
            main_config = result.stdout
    except subprocess.CalledProcessError as e:
        flash(f'Error reading main configuration: {e.stderr}', 'error')
    except Exception as e:
        flash(f'Error reading main configuration: {str(e)}', 'error')
    
    try:
        if os.path.exists(share_file):
            result = subprocess.run(
                ['sudo', 'cat', share_file],
                capture_output=True, text=True, check=True
            )
            share_config = result.stdout
    except subprocess.CalledProcessError as e:
        flash(f'Error reading share configuration: {e.stderr}', 'error')
    except Exception as e:
        flash(f'Error reading share configuration: {str(e)}', 'error')
    
    return render_template('edit_config.html', 
                          main_config=main_config,
                          share_config=share_config,
                          has_sudo=check_sudo_access())

@bp.route('/view-logs/<log_type>')
@login_required
def view_logs(log_type):
    """View Samba service logs"""
    if not check_sudo_access():
        flash('Error: Sudo access is required to view logs', 'error')
        return redirect('/maintenance')
    
    log_file = None
    log_title = None
    
    if log_type == 'smbd':
        log_file = '/var/log/samba/log.smbd'
        log_title = 'Samba Server (smbd) Logs'
    elif log_type == 'nmbd':
        log_file = '/var/log/samba/log.nmbd'
        log_title = 'Samba NetBIOS (nmbd) Logs'
    else:
        flash(f'Unknown log type: {log_type}', 'error')
        return redirect('/maintenance')
    
    try:
        # Use sudo to read the log file
        result = subprocess.run(['sudo', 'cat', log_file], capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            if 'No such file or directory' in result.stderr:
                log_content = f"Log file {log_file} does not exist. The service may not have generated logs yet."
            else:
                flash(f'Error reading log file: {result.stderr}', 'error')
                return redirect('/maintenance')
        else:
            log_content = result.stdout
            
            # If log is empty
            if not log_content.strip():
                log_content = "Log file is empty. No entries have been recorded yet."
        
        return render_template('view_logs.html', log_content=log_content, log_title=log_title, log_type=log_type)
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect('/maintenance')

@bp.route('/service/<action>')
@login_required
def service_action(action):
    """Perform service actions (start, stop, restart, status)"""
    if not check_sudo_access():
        flash('Error: Sudo access is required to manage services', 'error')
        return redirect('/')
    
    valid_actions = ['start', 'stop', 'restart', 'status']
    
    if action not in valid_actions:
        flash(f'Invalid action: {action}', 'error')
        return redirect('/')
    
    try:
        if action == 'status':
            status = get_samba_status()
            return jsonify(status)
        else:
            result = subprocess.run(['sudo', 'systemctl', action, 'smbd', 'nmbd'], 
                                   capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                flash(f'Error {action} Samba services: {result.stderr}', 'error')
            else:
                flash(f'Successfully {action}ed Samba services', 'success')
                
        return redirect('/')
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect('/')
