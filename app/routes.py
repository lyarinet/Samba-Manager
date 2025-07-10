from flask import Blueprint, render_template, request, redirect, flash, send_file
import io
from .samba_utils import *

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/global-settings', methods=['GET', 'POST'])
def global_settings():
    if request.method == 'POST':
        result = write_global_settings({
            'server string': request.form['server_string'],
            'workgroup': request.form['workgroup'],
            'log level': request.form['log_level']
        })
        flash('Settings saved' if result else 'Failed to save settings')
        return redirect('/global-settings')
    settings = read_global_settings()
    return render_template('global_settings.html', settings=settings)

@bp.route('/shares', methods=['GET', 'POST'])
def shares():
    if request.method == 'POST':
        if 'delete' in request.form:
            delete_share(request.form['name'])
            flash('Share deleted')
        else:
            share = {
                'name': request.form['name'],
                'path': request.form['path'],
                'read only': request.form.get('readonly', 'no'),
                'valid users': request.form.get('valid_users', ''),
                'vfs objects': request.form.get('vfs', ''),
            }
            if not os.path.exists(share['path']):
                os.makedirs(share['path'], exist_ok=True)
            add_or_update_share(share)
            flash('Share saved')
        return redirect('/shares')
    return render_template('shares.html', shares=load_shares(), users=list_system_users(), groups=list_system_groups())

@bp.route('/export')
def export():
    data = export_config()
    return send_file(io.BytesIO(data.encode()), mimetype='text/plain', as_attachment=True, download_name='smb_backup.conf')

@bp.route('/import', methods=['POST'])
def import_conf():
    file = request.files['file']
    content = file.read().decode()
    result = import_config(content)
    flash('Imported successfully' if result else 'Import failed')
    return redirect('/')
