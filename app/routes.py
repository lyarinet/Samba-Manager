from flask import Blueprint, render_template, request, redirect, flash, send_file
import io
import os
from .samba_utils import *

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # Get Samba service status
    status = get_samba_status()
    has_sudo = check_sudo_access()
    return render_template('index.html', status=status, has_sudo=has_sudo)

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
