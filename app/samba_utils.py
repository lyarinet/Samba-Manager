import os
import re
import subprocess

SMB_CONF = './smb.conf.template'  # instead of /etc/samba/smb.conf
SHARE_CONF = './shares.conf'      # instead of /etc/samba/shares.conf


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
        return {'error': str(e)}

def write_global_settings(settings):
    try:
        print("Writing settings:", settings)  # <-- Add this
        with open(SMB_CONF, 'r') as f:
            data = f.read()
        for key, val in settings.items():
            data = re.sub(rf'{key}\s*=.*', f'{key} = {val}', data)
        with open(SMB_CONF, 'w') as f:
            f.write(data)
        return True
    except Exception as e:
        print("Error:", e)  # <-- Add this
        return False


def load_shares():
    shares = []
    if not os.path.exists(SHARE_CONF):
        return shares
    with open(SHARE_CONF, 'r') as f:
        block = {}
        for line in f:
            line = line.strip()
            if line.startswith('['):
                if block:
                    shares.append(block)
                block = {'name': line.strip('[]')}
            elif '=' in line:
                key, value = [x.strip() for x in line.split('=', 1)]
                block[key] = value
        if block:
            shares.append(block)
    return shares

def save_shares(shares):
    with open(SHARE_CONF, 'w') as f:
        for s in shares:
            f.write(f"[{s['name']}]\n")
            for key in s:
                if key != 'name':
                    f.write(f"   {key} = {s[key]}\n")
            f.write('\n')

def add_or_update_share(new_share):
    shares = load_shares()
    for idx, s in enumerate(shares):
        if s['name'] == new_share['name']:
            shares[idx] = new_share
            break
    else:
        shares.append(new_share)
    save_shares(shares)

def delete_share(name):
    shares = [s for s in load_shares() if s['name'] != name]
    save_shares(shares)

def list_system_users():
    output = subprocess.check_output(['getent', 'passwd']).decode()
    return [line.split(':')[0] for line in output.strip().split('\n') if int(line.split(':')[2]) >= 1000]

def list_system_groups():
    output = subprocess.check_output(['getent', 'group']).decode()
    return [line.split(':')[0] for line in output.strip().split('\n') if int(line.split(':')[2]) >= 1000]

def export_config():
    with open(SMB_CONF, 'r') as f1, open(SHARE_CONF, 'r') as f2:
        return f1.read() + '\n' + f2.read()

def import_config(data):
    parts = data.split('[global]')
    if len(parts) >= 2:
        global_conf = '[global]' + parts[1].split('[', 1)[0]
        rest = '[' + parts[1].split('[', 1)[1]
        with open(SMB_CONF, 'w') as f1:
            f1.write(global_conf.strip() + '\n')
        with open(SHARE_CONF, 'w') as f2:
            f2.write(rest.strip() + '\n')
        return True
    return False
