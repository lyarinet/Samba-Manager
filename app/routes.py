from flask import Blueprint, render_template, request, redirect, flash, send_file, url_for
import io
import os
import subprocess
from .samba_utils import *

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # Get Samba service status
    status = get_samba_status()
    has_sudo = check_sudo_access()
    
    # Get Samba installation status
    installation_status = get_samba_installation_status()
    
    return render_template('index.html', status=status, has_sudo=has_sudo, installation_status=installation_status)

@bp.route('/global-settings', methods=['GET', 'POST'])
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
        
    settings = read_global_settings()
    has_sudo = check_sudo_access()
    return render_template('global_settings.html', settings=settings, has_sudo=has_sudo)

@bp.route('/shares', methods=['GET', 'POST'])
def shares():
    if request.method == 'POST':
        if not check_sudo_access():
            flash('Error: Sudo access is required to modify Samba shares', 'error')
            return redirect('/shares')
            
        if 'delete' in request.form:
            share_name = request.form['name']
            # Check if it's a system share
            if share_name in ['secure-share', 'share']:
                flash(f'Cannot delete system share "{share_name}". Edit /etc/samba/smb.conf directly.', 'error')
                return redirect('/shares')
                
            result = delete_share(share_name)
            if result:
                flash('Share deleted and Samba service restarted', 'success')
            else:
                flash('Failed to delete share', 'error')
        else:
            path = request.form['path']
            
            # Validate path
            valid, message = validate_share_path(path)
            if not valid and not os.path.exists(path):
                # Try to create the directory
                try:
                    os.makedirs(path, exist_ok=True)
                    valid = os.path.exists(path)
                    if valid:
                        message = "Path created successfully"
                except Exception as e:
                    message = f"Failed to create path: {str(e)}"
            
            if not valid:
                flash(f'Invalid path: {message}', 'error')
                return redirect('/shares')
                
            share = {
                'name': request.form['name'],
                'path': path,
                'read only': request.form.get('readonly', 'no'),
                'valid users': request.form.get('valid_users', ''),
                'vfs objects': request.form.get('vfs', ''),
            }
            
            # Check if it's trying to override a system share
            if share['name'] in ['secure-share', 'share']:
                flash(f'Cannot modify system share "{share["name"]}". Edit /etc/samba/smb.conf directly.', 'error')
                return redirect('/shares')
            
            result = add_or_update_share(share)
            if result:
                flash('Share saved and Samba service restarted', 'success')
            else:
                flash('Failed to save share', 'error')
                
        return redirect('/shares')
        
    has_sudo = check_sudo_access()
    all_shares = load_shares()
    
    # Sort shares: system shares first, then local shares
    system_shares = [s for s in all_shares if s['name'] in ['secure-share', 'share']]
    local_shares = [s for s in all_shares if s['name'] not in ['secure-share', 'share']]
    sorted_shares = system_shares + local_shares
    
    return render_template('shares.html', 
                          shares=sorted_shares, 
                          users=list_system_users(), 
                          groups=list_system_groups(),
                          has_sudo=has_sudo)

@bp.route('/users', methods=['GET'])
def users():
    if not check_sudo_access():
        flash('Error: Sudo access is required to manage Samba users', 'error')
        return redirect('/')
        
    samba_users = get_samba_users()
    system_users = list_system_users()
    system_groups = list_system_groups()
    
    return render_template('users.html', 
                          samba_users=samba_users, 
                          system_users=system_users,
                          system_groups=system_groups,
                          has_sudo=check_sudo_access())

@bp.route('/users/add', methods=['POST'])
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
def export():
    data = export_config()
    if data.startswith("Error"):
        flash(data, 'error')
        return redirect('/')
    return send_file(io.BytesIO(data.encode()), mimetype='text/plain', as_attachment=True, download_name='smb_backup.conf')

@bp.route('/import', methods=['POST'])
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
    
    return render_template('setup.html', 
                          installation_status=installation_status,
                          has_sudo=check_sudo_access())

@bp.route('/fix-permissions', methods=['POST'])
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
def maintenance():
    """Maintenance page for Samba"""
    if not check_sudo_access():
        flash('Error: Sudo access is required to access maintenance functions', 'error')
        return redirect('/')
    
    # Get current installation status
    installation_status = get_samba_installation_status()
    
    return render_template('maintenance.html', 
                          installation_status=installation_status,
                          has_sudo=check_sudo_access())

@bp.route('/install-samba', methods=['POST'])
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
