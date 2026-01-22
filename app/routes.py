from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash,
    send_file,
    url_for,
    jsonify,
)
from flask_login import login_required, current_user
import io
import os
import subprocess
import tempfile
import datetime
from .samba_utils import *
import json
import re
import pwd, grp

bp = Blueprint("main", __name__)


def validate_share_name(name):
    """Validate share name for security and Samba compatibility"""
    if not name:
        return False, "Share name cannot be empty"

    if len(name) > 80:
        return False, "Share name too long (max 80 characters)"

    # Samba share names can contain letters, numbers, underscores, hyphens
    # Must not contain spaces or special characters that could cause issues
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return (
            False,
            "Share name can only contain letters, numbers, underscores, and hyphens",
        )

    # Reserved names
    reserved_names = ["global", "homes", "printers", "print$"]
    if name.lower() in reserved_names:
        return False, "Share name is reserved by Samba"

    return True, "Valid"


def validate_share_path(path):
    """Enhanced path validation for security"""
    if not path:
        return False, "Path cannot be empty"

    # Convert to absolute path
    abs_path = os.path.abspath(path)

    # Check for directory traversal attempts
    if ".." in abs_path or not abs_path.startswith("/"):
        return False, "Invalid path - directory traversal not allowed"

    # Check if path exists and is a directory
    if not os.path.exists(abs_path):
        return False, "Path does not exist"
    elif not os.path.isdir(abs_path):
        return False, "Path must be a directory"

    # Check if path is within reasonable system limits
    if len(abs_path) > 4096:  # PATH_MAX on most systems
        return False, "Path too long"

    # Avoid sensitive system directories
    sensitive_paths = [
        "/etc",
        "/var",
        "/usr",
        "/bin",
        "/sbin",
        "/boot",
        "/sys",
        "/proc",
        "/dev",
    ]
    for sensitive in sensitive_paths:
        if abs_path.startswith(sensitive):
            return False, f"Cannot use system directory: {sensitive}"

    return True, f"Path validated: {abs_path}"


@bp.route("/")
@login_required
def index():
    # Get Samba service status
    status = get_samba_status()
    has_sudo = check_sudo_access()

    # Get Samba installation status
    installation_status = get_samba_installation_status()

    # Add datetime for the template
    now = datetime.datetime.now()

    return render_template(
        "index.html",
        status=status,
        has_sudo=has_sudo,
        installation_status=installation_status,
        now=now,
    )


@bp.route("/global-settings", methods=["GET", "POST"])
@login_required
def global_settings():
    if request.method == "POST":
        if not check_sudo_access():
            flash("Error: Sudo access is required to modify Samba settings", "error")
            return redirect("/global-settings")

        # Collect all submitted form fields
        settings = {
            "server string": request.form["server_string"],
            "workgroup": request.form["workgroup"],
            "log level": request.form["log_level"],
        }

        # Add optional fields if they exist in the form
        optional_fields = [
            ("server_role", "server role"),
            ("log_file", "log file"),
            ("max_log_size", "max log size"),
            ("security", "security"),
            ("encrypt_passwords", "encrypt passwords"),
            ("guest_account", "guest account"),
            ("map_to_guest", "map to guest"),
            ("interfaces", "interfaces"),
            ("bind_interfaces_only", "bind interfaces only"),
            ("unix_charset", "unix charset"),
            ("dos_charset", "dos charset"),
            ("deadtime", "deadtime"),
            ("keepalive", "keepalive"),
            ("max_connections", "max connections"),
            ("socket_options", "socket options"),
            ("dns_proxy", "dns proxy"),
            ("usershare_allow_guests", "usershare allow guests"),
        ]

        for form_name, samba_name in optional_fields:
            if form_name in request.form and request.form[form_name]:
                settings[samba_name] = request.form[form_name]

        # Always include hosts_allow and hosts_deny, even if empty
        settings["hosts allow"] = request.form.get("hosts_allow", "")
        settings["hosts deny"] = request.form.get("hosts_deny", "")

        result = write_global_settings(settings)

        if result:
            flash("Settings saved and Samba service restarted", "success")
        else:
            flash("Failed to save settings. Check logs for details", "error")

        return redirect("/global-settings")

    global_settings = read_global_settings()
    has_sudo = check_sudo_access()

    # Get Samba service status
    status = get_samba_status()

    return render_template(
        "global_settings.html",
        global_settings=global_settings,
        status=status,
        has_sudo=has_sudo,
    )


@bp.route("/shares", methods=["GET", "POST"])
@login_required
def shares():
    has_sudo = check_sudo_access()
    all_shares = load_shares()

    # Sort shares: system shares first, then local shares
    system_shares = [s for s in all_shares if s["name"] in ["secure-share", "share"]]
    local_shares = [s for s in all_shares if s["name"] not in ["secure-share", "share"]]
    sorted_shares = system_shares + local_shares

    return render_template(
        "shares.html",
        shares=sorted_shares,
        users=list_system_users(),
        groups=list_system_groups(),
        has_sudo=has_sudo,
    )


@bp.route("/add-share", methods=["POST"])
@login_required
def add_share():
    has_sudo = check_sudo_access()
    if not has_sudo:
        flash("Error: Sudo access is required to add shares", "error")
        return redirect("/shares")

    name = request.form["name"]
    path = request.form["path"]

    # Validate share name
    valid_name, name_message = validate_share_name(name)
    if not valid_name:
        flash(f"Invalid share name: {name_message}", "error")
        return redirect("/shares")

    # Check if share name already exists
    all_shares = load_shares()
    if any(s["name"] == name for s in all_shares):
        flash(f'A share with the name "{name}" already exists', "error")
        return redirect("/shares")

    # Check if it's trying to override a system share
    if name in ["secure-share", "share"]:
        flash(
            f'Cannot create system share "{name}". Edit /etc/samba/smb.conf directly.',
            "error",
        )
        return redirect("/shares")

    # Validate and create path if needed
    valid, message = validate_share_path(path)
    if not valid:
        flash(f"Invalid path: {message}", "error")
        return redirect("/shares")

    # Process users and groups
    valid_users = request.form.get("valid_users", "")
    valid_groups = request.form.getlist("valid_groups")

    # Combine users and groups for valid_users field
    if valid_groups:
        if valid_users:
            valid_users = valid_users + "," + ",".join(valid_groups)
        else:
            valid_users = ",".join(valid_groups)

    # Process write list users and groups
    write_list = request.form.get("write_list", "")
    write_groups = request.form.getlist("write_groups")

    # Combine users and groups for write_list field
    if write_groups:
        if write_list:
            write_list = write_list + "," + ",".join(write_groups)
        else:
            write_list = ",".join(write_groups)

    # Create new share with normalized key names
    share = {
        "name": name,
        "path": path,
        "comment": request.form.get("comment", ""),
        "browseable": "yes" if request.form.get("browseable") else "no",
        "read_only": "yes" if request.form.get("read_only") else "no",
        "guest_ok": "yes" if request.form.get("guest_ok") else "no",
        "valid_users": valid_users,
        "write_list": write_list,
        "create_mask": request.form.get("create_mask", "0744"),
        "directory_mask": request.form.get("directory_mask", "0755"),
        "force_group": "smbusers",
        "max_connections": request.form.get("max_connections", "10"),
    }

    result = add_or_update_share(share)
    if result:
        flash("Share added successfully and Samba service restarted", "success")
    else:
        flash("Failed to add share", "error")

    return redirect("/shares")


@bp.route("/edit-share", methods=["POST"])
@login_required
def edit_share():
    has_sudo = check_sudo_access()
    if not has_sudo:
        flash("Error: Sudo access is required to modify shares", "error")
        return redirect("/shares")

    original_name = request.form["original_name"]
    name = request.form["name"]
    path = request.form["path"]

    # Check if it's a system share
    if original_name in ["secure-share", "share"]:
        flash(
            f'Cannot modify system share "{original_name}". Edit /etc/samba/smb.conf directly.',
            "error",
        )
        return redirect("/shares")

    # Check if new name already exists (if name was changed)
    if original_name != name:
        all_shares = load_shares()
        if any(s["name"] == name for s in all_shares):
            flash(f'A share with the name "{name}" already exists', "error")
            return redirect("/shares")

    # Validate and create path if needed
    valid, message = validate_share_path(path)
    if not valid:
        flash(f"Invalid path: {message}", "error")
        return redirect("/shares")
    else:
        print(f"Path validation successful: {message}")

    # Process users and groups
    valid_users = request.form.get("valid_users", "")
    valid_groups = request.form.getlist("valid_groups")

    # Combine users and groups for valid_users field
    if valid_groups:
        if valid_users:
            valid_users = valid_users + "," + ",".join(valid_groups)
        else:
            valid_users = ",".join(valid_groups)

    # Process write list users and groups
    write_list = request.form.get("write_list", "")
    write_groups = request.form.getlist("write_groups")

    # Combine users and groups for write_list field
    if write_groups:
        if write_list:
            write_list = write_list + "," + ",".join(write_groups)
        else:
            write_list = ",".join(write_groups)

    # Update share with normalized key names
    share = {
        "name": name,
        "path": path,
        "comment": request.form.get("comment", ""),
        "browseable": "yes" if request.form.get("browseable") else "no",
        "read_only": "yes" if request.form.get("read_only") else "no",
        "guest_ok": "yes" if request.form.get("guest_ok") else "no",
        "valid_users": valid_users,
        "write_list": write_list,
        "create_mask": request.form.get("create_mask", "0744"),
        "directory_mask": request.form.get("directory_mask", "0755"),
        "force_group": "smbusers",
        "max_connections": request.form.get("max_connections", "10"),
    }

    # If name was changed, delete the old share first
    if original_name != name:
        delete_share(original_name)

    result = add_or_update_share(share)
    if result:
        flash("Share updated successfully and Samba service restarted", "success")
    else:
        flash("Failed to update share", "error")

    return redirect("/shares")


@bp.route("/delete-share", methods=["POST"])
@login_required
def delete_share_route():
    has_sudo = check_sudo_access()
    if not has_sudo:
        flash("Error: Sudo access is required to delete shares", "error")
        return redirect("/shares")

    share_name = request.form["name"]

    # Check if it's a system share
    if share_name in ["secure-share", "share"]:
        flash(
            f'Cannot delete system share "{share_name}". Edit /etc/samba/smb.conf directly.',
            "error",
        )
        return redirect("/shares")

    result = delete_share(share_name)
    if result:
        flash("Share deleted successfully and Samba service restarted", "success")
    else:
        flash("Failed to delete share", "error")

    # Force a page refresh to update the UI
    return redirect("/shares")


@bp.route("/users", methods=["GET"])
@login_required
def users():
    if not check_sudo_access():
        flash("Error: Sudo access is required to manage Samba users", "error")
        return redirect("/")

    users = get_samba_users()
    system_users = list_system_users()
    system_groups = list_system_groups()

    return render_template(
        "users.html",
        users=users,
        system_users=system_users,
        groups=system_groups,
        has_sudo=check_sudo_access(),
    )


@bp.route("/users/add", methods=["POST"])
@login_required
def add_user():
    if not check_sudo_access():
        flash("Error: Sudo access is required to manage Samba users", "error")
        return redirect("/users")

    username = request.form.get("username")
    password = request.form.get("password")
    create_system_user = request.form.get("create_system_user") == "on"

    if not username or not password:
        flash("Username and password are required", "error")
        return redirect("/users")

    result = add_samba_user(username, password, create_system_user)

    if result:
        flash(f"User {username} added successfully", "success")
    else:
        flash(f"Failed to add user {username}", "error")

    return redirect("/users")


@bp.route("/users/reset-password/<username>", methods=["POST"])
@login_required
def reset_samba_password(username):
    """Reset a Samba user's password"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to reset passwords", "error")
        return redirect("/users")

    password = request.form.get("password")
    if not password:
        flash("Password is required", "error")
        return redirect("/users")

    try:
        # Use smbpasswd to reset the password
        process = subprocess.Popen(
            ["sudo", "smbpasswd", "-s", username],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Send the password twice (for confirmation)
        stdout, stderr = process.communicate(input=f"{password}\n{password}\n")

        if process.returncode != 0:
            flash(f"Failed to reset password: {stderr}", "error")
        else:
            flash(f"Password for {username} reset successfully", "success")

    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return redirect("/users")


@bp.route("/users/disable/<username>", methods=["POST"])
@login_required
def disable_samba_user(username):
    """Disable a Samba user"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to disable users", "error")
        return redirect("/users")

    try:
        # Use smbpasswd to disable the user
        result = subprocess.run(
            ["sudo", "smbpasswd", "-d", username],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            flash(f"Failed to disable user: {result.stderr}", "error")
        else:
            flash(f"User {username} disabled successfully", "success")

    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return redirect("/users")


@bp.route("/users/enable/<username>", methods=["POST"])
@login_required
def enable_samba_user(username):
    """Enable a Samba user"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to enable users", "error")
        return redirect("/users")

    try:
        # Use smbpasswd to enable the user
        result = subprocess.run(
            ["sudo", "smbpasswd", "-e", username],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            flash(f"Failed to enable user: {result.stderr}", "error")
        else:
            flash(f"User {username} enabled successfully", "success")

    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return redirect("/users")


@bp.route("/users/delete/<username>", methods=["POST"])
@login_required
def delete_samba_user(username):
    """Delete a Samba user"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to delete users", "error")
        return redirect("/users")

    try:
        # Use smbpasswd to delete the user
        result = subprocess.run(
            ["sudo", "smbpasswd", "-x", username],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            flash(f"Failed to delete user: {result.stderr}", "error")
        else:
            flash(f"User {username} deleted successfully", "success")

    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return redirect("/users")


@bp.route("/export")
@login_required
def export():
    data = export_config()
    if data.startswith("Error"):
        flash(data, "error")
        return redirect("/")
    return send_file(
        io.BytesIO(data.encode()),
        mimetype="text/plain",
        as_attachment=True,
        download_name="smb_backup.conf",
    )


@bp.route("/import", methods=["POST"])
@login_required
def import_conf():
    if not check_sudo_access():
        flash("Error: Sudo access is required to import configuration", "error")
        return redirect("/maintenance")

    if "config_file" not in request.files:
        flash("No file part in the request", "error")
        return redirect("/maintenance")

    file = request.files["config_file"]

    if file.filename == "":
        flash("No file selected", "error")
        return redirect("/maintenance")

    # Check file extension
    allowed_extensions = [".json", ".conf"]
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        flash(
            f'File must be one of these types: {", ".join(allowed_extensions)}', "error"
        )
        return redirect("/maintenance")

    try:
        # Create a temporary file to store the uploaded content
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)

            if file_ext == ".json":
                # Handle JSON import
                with open(temp_file.name, "r") as f:
                    config_data = json.load(f)

                # Process the imported JSON data
                result = import_config(config_data)

                if result:
                    flash("Configuration imported successfully", "success")
                else:
                    flash("Failed to import configuration", "error")

            elif file_ext == ".conf":
                # Handle direct .conf file import
                # Copy the uploaded file to the Samba configuration
                backup_path = "/etc/samba/smb_backup.conf"

                # Create a backup of the current config
                subprocess.run(
                    ["sudo", "cp", "/etc/samba/smb.conf", backup_path], check=False
                )

                # Copy the uploaded file to smb.conf
                subprocess.run(
                    ["sudo", "cp", temp_file.name, "/etc/samba/smb.conf"], check=False
                )

                # Validate the configuration
                validate_cmd = subprocess.run(
                    ["sudo", "testparm", "-s", "/etc/samba/smb.conf"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if validate_cmd.returncode != 0:
                    # If validation fails, restore the backup
                    subprocess.run(
                        ["sudo", "cp", backup_path, "/etc/samba/smb.conf"], check=False
                    )
                    flash(f"Invalid configuration file: {validate_cmd.stderr}", "error")
                else:
                    # Restart Samba services
                    subprocess.run(
                        ["sudo", "systemctl", "restart", "smbd", "nmbd"], check=False
                    )
                    flash("Configuration file imported successfully", "success")

            # Clean up the temporary file
            os.unlink(temp_file.name)

    except Exception as e:
        flash(f"Error importing configuration: {str(e)}", "error")

    return redirect("/maintenance")


@bp.route("/restart")
@login_required
def restart_service():
    if not check_sudo_access():
        flash("Error: Sudo access is required to restart Samba service", "error")
        return redirect("/")

    result = restart_samba_service()

    if result:
        flash("Samba service restarted successfully", "success")
    else:
        flash("Failed to restart Samba service", "error")

    return redirect("/")


@bp.route("/setup", methods=["GET", "POST"])
@login_required
def setup():
    """Setup Samba from the web interface"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to set up Samba", "error")
        return redirect("/")

    if request.method == "POST":
        result = setup_samba()
        if result:
            flash("Samba has been set up successfully", "success")
        else:
            flash("Failed to set up Samba. Check logs for details", "error")
        return redirect("/")

    # Get current installation status
    installation_status = get_samba_installation_status()

    # Get Samba service status
    status = get_samba_status()

    return render_template(
        "setup.html",
        installation_status=installation_status,
        status=status,
        has_sudo=check_sudo_access(),
    )


@bp.route("/quick-setup", methods=["POST"])
@login_required
def quick_setup():
    """Quick setup for Samba with basic configuration"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to set up Samba", "error")
        return redirect("/setup")

    share_name = request.form.get("share_name", "share")
    share_path = request.form.get("share_path", "/srv/samba/share")
    workgroup = request.form.get("workgroup", "WORKGROUP")
    guest_access = "yes" if request.form.get("guest_access") else "no"

    try:
        # Create share directory if it doesn't exist
        create_share_directory(share_name, share_path)

        # Configure global settings
        global_settings = {
            "server string": "Samba Server",
            "workgroup": workgroup,
            "log level": "1",
            "map to guest": "Bad User" if guest_access == "yes" else "Never",
        }

        write_global_settings(global_settings)

        # Create share
        share = {
            "name": share_name,
            "path": share_path,
            "read_only": "no",
            "valid_users": "@smbusers" if guest_access == "no" else "",
            "guest_ok": guest_access,
            "browseable": "yes",
            "create_mask": "0770",
            "directory_mask": "0770",
            "force_group": "smbusers",
        }

        result = add_or_update_share(share)

        if result:
            flash("Quick setup completed successfully", "success")
        else:
            flash("Failed to complete quick setup", "error")

    except Exception as e:
        flash(f"Error during quick setup: {str(e)}", "error")

    return redirect("/setup")


@bp.route("/fix-permissions", methods=["POST"])
@login_required
def fix_permissions():
    """Fix permissions on share directories"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to fix permissions", "error")
        return redirect("/")

    result = fix_share_permissions()
    if result:
        flash("Share permissions have been fixed successfully", "success")
    else:
        flash("Failed to fix share permissions. Check logs for details", "error")

    return redirect("/")


@bp.route("/maintenance")
@login_required
def maintenance():
    """Maintenance page for Samba"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to access maintenance functions", "error")
        return redirect("/")

    # Get current installation status
    installation_status = get_samba_installation_status()

    # Get Samba service status
    status = get_samba_status()

    # Get shares for permission management
    shares = load_shares()

    return render_template(
        "maintenance.html",
        installation_status=installation_status,
        status=status,
        shares=shares,
        has_sudo=check_sudo_access(),
    )


@bp.route("/install", methods=["POST"])
@login_required
def install_samba_route():
    """Install Samba from the web interface"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to install Samba", "error")
        return redirect("/setup")

    try:
        result = ensure_samba_installed()
        if result:
            flash("Samba has been installed successfully", "success")
        else:
            flash("Failed to install Samba. Check logs for details", "error")
    except Exception as e:
        flash(f"Error installing Samba: {str(e)}", "error")

    return redirect("/setup")


@bp.route("/start-service", methods=["POST"])
@login_required
def start_service():
    """Start the Samba service"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to start Samba service", "error")
        return redirect("/maintenance")

    try:
        if DEV_MODE:
            flash("[DEV MODE] Would start Samba service in production", "info")
            return redirect("/maintenance")

        subprocess.run(["sudo", "systemctl", "start", "smbd"], check=True)
        subprocess.run(["sudo", "systemctl", "start", "nmbd"], check=True)
        flash("Samba service started successfully", "success")
    except Exception as e:
        flash(f"Failed to start Samba service: {str(e)}", "error")

    return redirect("/maintenance")


@bp.route("/stop-service", methods=["POST"])
@login_required
def stop_service():
    """Stop the Samba service"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to stop Samba service", "error")
        return redirect("/maintenance")

    try:
        if DEV_MODE:
            flash("[DEV MODE] Would stop Samba service in production", "info")
            return redirect("/maintenance")

        subprocess.run(["sudo", "systemctl", "stop", "smbd"], check=True)
        subprocess.run(["sudo", "systemctl", "stop", "nmbd"], check=True)
        flash("Samba service stopped successfully", "success")
    except Exception as e:
        flash(f"Failed to stop Samba service: {str(e)}", "error")

    return redirect("/maintenance")


@bp.route("/edit-config", methods=["GET", "POST"])
@login_required
def edit_config():
    """Edit Samba configuration file directly"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to edit Samba configuration", "error")
        return redirect("/")

    config_file = SMB_CONF
    share_file = SHARE_CONF

    if request.method == "POST":
        if "main_config" in request.form:
            try:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
                    temp_file.write(request.form["main_config"])
                    temp_path = temp_file.name

                # Use sudo to move the file to the correct location
                result = subprocess.run(
                    ["sudo", "cp", temp_path, config_file],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                os.unlink(temp_path)  # Remove the temp file
                flash("Main configuration file updated successfully", "success")
            except subprocess.CalledProcessError as e:
                flash(f"Error updating main configuration: {e.stderr}", "error")
            except Exception as e:
                flash(f"Error updating main configuration: {str(e)}", "error")

        if "share_config" in request.form:
            try:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
                    temp_file.write(request.form["share_config"])
                    temp_path = temp_file.name

                # Use sudo to move the file to the correct location
                result = subprocess.run(
                    ["sudo", "cp", temp_path, share_file],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                os.unlink(temp_path)  # Remove the temp file
                flash("Share configuration file updated successfully", "success")
            except subprocess.CalledProcessError as e:
                flash(f"Error updating share configuration: {e.stderr}", "error")
            except Exception as e:
                flash(f"Error updating share configuration: {str(e)}", "error")

        # Restart Samba service after config changes
        if restart_samba_service():
            flash("Samba service restarted successfully", "success")
        else:
            flash("Failed to restart Samba service", "error")

        return redirect("/edit-config")

    # Read configuration files
    main_config = ""
    share_config = ""

    try:
        if os.path.exists(config_file):
            result = subprocess.run(
                ["sudo", "cat", config_file], capture_output=True, text=True, check=True
            )
            main_config = result.stdout
    except subprocess.CalledProcessError as e:
        flash(f"Error reading main configuration: {e.stderr}", "error")
    except Exception as e:
        flash(f"Error reading main configuration: {str(e)}", "error")

    try:
        if os.path.exists(share_file):
            result = subprocess.run(
                ["sudo", "cat", share_file], capture_output=True, text=True, check=True
            )
            share_config = result.stdout
    except subprocess.CalledProcessError as e:
        flash(f"Error reading share configuration: {e.stderr}", "error")
    except Exception as e:
        flash(f"Error reading share configuration: {str(e)}", "error")

    return render_template(
        "edit_config.html",
        main_config=main_config,
        share_config=share_config,
        has_sudo=check_sudo_access(),
    )


@bp.route("/view-logs/<log_type>")
@login_required
def view_logs(log_type):
    """View Samba service logs"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to view logs", "error")
        return redirect("/maintenance")

    log_file = None
    log_title = None

    if log_type == "smbd":
        log_file = "/var/log/samba/log.smbd"
        log_title = "Samba Server (smbd) Logs"
    elif log_type == "nmbd":
        log_file = "/var/log/samba/log.nmbd"
        log_title = "Samba NetBIOS (nmbd) Logs"
    else:
        flash(f"Unknown log type: {log_type}", "error")
        return redirect("/maintenance")

    try:
        # Use sudo to read the log file
        result = subprocess.run(
            ["sudo", "cat", log_file], capture_output=True, text=True, check=False
        )

        if result.returncode != 0:
            if "No such file or directory" in result.stderr:
                log_content = f"Log file {log_file} does not exist. The service may not have generated logs yet."
            else:
                flash(f"Error reading log file: {result.stderr}", "error")
                return redirect("/maintenance")
        else:
            log_content = result.stdout

            # If log is empty
            if not log_content.strip():
                log_content = "Log file is empty. No entries have been recorded yet."

        return render_template(
            "view_logs.html",
            log_content=log_content,
            log_title=log_title,
            log_type=log_type,
        )

    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect("/maintenance")


@bp.route("/service/<action>")
@login_required
def service_action(action):
    """Perform service actions (start, stop, restart, status)"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to manage services", "error")
        return redirect("/maintenance")

    valid_actions = ["start", "stop", "restart", "status", "enable"]

    if action not in valid_actions:
        flash(f"Invalid action: {action}", "error")
        return redirect("/maintenance")

    try:
        if action == "status":
            status = get_samba_status()
            return jsonify(status)
        elif action == "enable":
            subprocess.run(
                ["sudo", "systemctl", "enable", "smbd", "nmbd"],
                capture_output=True,
                text=True,
                check=False,
            )
            flash("Samba services enabled to start on boot", "success")
        else:
            result = subprocess.run(
                ["sudo", "systemctl", action, "smbd", "nmbd"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                flash(f"Error {action} Samba services: {result.stderr}", "error")
            else:
                flash(f"Successfully {action}ed Samba services", "success")

        return redirect("/maintenance")

    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect("/maintenance")


@bp.route("/groups", methods=["GET"])
@login_required
def groups():
    if not check_sudo_access():
        flash("Error: Sudo access is required to manage system groups", "error")
        return redirect("/")

    system_groups = list_system_groups()

    return render_template(
        "groups.html", groups=system_groups, has_sudo=check_sudo_access()
    )


@bp.route("/groups/add", methods=["POST"])
@login_required
def add_group():
    if not check_sudo_access():
        flash("Error: Sudo access is required to manage system groups", "error")
        return redirect("/groups")

    group_name = request.form.get("group_name")

    if not group_name:
        flash("Group name is required", "error")
        return redirect("/groups")

    # Check if the group already exists
    existing_groups = list_system_groups()
    if group_name in existing_groups:
        flash(f"Group {group_name} already exists", "error")
        return redirect("/groups")

    # Validate group name format
    if not re.match(r"^[a-z][\w-]*$", group_name):
        flash(
            f"Invalid group name: {group_name} - Group names must start with a letter and contain only letters, numbers, hyphens, and underscores",
            "error",
        )
        return redirect("/groups")

    # Create the group
    result = create_system_group(group_name)

    if result:
        flash(f"Group {group_name} created successfully", "success")
    else:
        flash(
            f"Failed to create group {group_name}. Check server logs for details.",
            "error",
        )

    return redirect("/groups")


@bp.route("/groups/delete/<group_name>", methods=["POST"])
@login_required
def delete_group(group_name):
    if not check_sudo_access():
        flash("Error: Sudo access is required to manage system groups", "error")
        return redirect("/groups")

    # Check if the group exists
    existing_groups = list_system_groups()
    if group_name not in existing_groups:
        flash(f"Group {group_name} does not exist", "error")
        return redirect("/groups")

    # Try to delete the group (this will handle primary group changes if needed)
    result = delete_system_group(group_name)

    if result:
        flash(f"Group {group_name} deleted successfully", "success")
    else:
        # Check if it's a primary group issue
        try:
            import pwd

            primary_users = []
            for user in pwd.getpwall():
                if user.pw_gid == grp.getgrnam(group_name).gr_gid:
                    primary_users.append(user.pw_name)

            if primary_users:
                flash(
                    f'Failed to delete group {group_name}. It is the primary group for user(s): {", ".join(primary_users)}. Try changing their primary group first.',
                    "error",
                )
            else:
                flash(
                    f"Failed to delete group {group_name}. Check server logs for details.",
                    "error",
                )
        except Exception:
            flash(
                f"Failed to delete group {group_name}. Check server logs for details.",
                "error",
            )

    return redirect("/groups")


@bp.route("/help")
@login_required
def help_page():
    """View the help and documentation page"""
    return render_template("help.html")


@bp.route("/api/shares", methods=["GET"])
@login_required
def api_shares():
    """API endpoint for shares"""
    all_shares = load_shares()

    # Convert to simpler JSON format
    shares_json = [
        {
            "name": share.get("name", ""),
            "path": share.get("path", ""),
            "browseable": share.get("browseable", "no") == "yes",
            "read_only": share.get("read_only", "yes") == "yes",
            "guest_ok": share.get("guest_ok", "no") == "yes",
            "valid_users": share.get("valid_users", ""),
            "max_connections": share.get("max_connections", "0"),
        }
        for share in all_shares
    ]

    return jsonify(shares_json)


@bp.route("/api/status", methods=["GET"])
@login_required
def api_status():
    """API endpoint for service status"""
    status = get_samba_status()
    return jsonify(status)


@bp.route("/api/connections", methods=["GET"])
@login_required
def api_connections():
    """API endpoint for active connections"""
    if not check_sudo_access():
        return jsonify({"error": "Sudo access required to view connections"}), 403

    connections = get_active_connections()
    return jsonify(connections)


@bp.route("/api/disk-usage", methods=["GET"])
@login_required
def api_disk_usage():
    """API endpoint for disk usage"""
    if not check_sudo_access():
        return jsonify({"error": "Sudo access required to view disk usage"}), 403

    usage_stats = get_share_usage_stats()
    return jsonify(usage_stats)


@bp.route("/api/backups", methods=["GET"])
@login_required
def api_backups():
    """API endpoint for available backups"""
    if not check_sudo_access():
        return jsonify({"error": "Sudo access required to view backups"}), 403

    backups = list_backups()
    return jsonify(backups)


@bp.route("/backups", methods=["GET"])
@login_required
def backups():
    """View and manage backups"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to manage backups", "error")
        return redirect("/")

    all_backups = list_backups()

    return render_template(
        "backups.html", backups=all_backups, has_sudo=check_sudo_access()
    )


@bp.route("/create-backup", methods=["POST"])
@login_required
def create_backup_route():
    """Create a new backup"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to create backups", "error")
        return redirect("/backups")

    success, result = create_backup()

    if success:
        flash(f"Backup created successfully: {os.path.basename(result)}", "success")
    else:
        flash(f"Failed to create backup: {result}", "error")

    return redirect("/backups")


@bp.route("/restore-backup/<filename>", methods=["POST"])
@login_required
def restore_backup_route(filename):
    """Restore from a backup file"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to restore backups", "error")
        return redirect("/backups")

    # Validate the filename format
    if not filename.startswith("samba_backup_") or not filename.endswith(".tar.gz"):
        flash("Invalid backup filename", "error")
        return redirect("/backups")

    backup_dir = "/var/lib/samba_manager/backups"
    backup_file = os.path.join(backup_dir, filename)

    # Check if the file exists
    if not os.path.exists(backup_file):
        flash(f"Backup file {filename} not found", "error")
        return redirect("/backups")

    success, message = restore_backup(backup_file)

    if success:
        flash("Backup restored successfully", "success")
    else:
        flash(f"Failed to restore backup: {message}", "error")

    return redirect("/backups")


@bp.route("/delete-backup/<filename>", methods=["POST"])
@login_required
def delete_backup_route(filename):
    """Delete a backup file"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to delete backups", "error")
        return redirect("/backups")

    # Validate the filename format
    if not filename.startswith("samba_backup_") or not filename.endswith(".tar.gz"):
        flash("Invalid backup filename", "error")
        return redirect("/backups")

    backup_dir = "/var/lib/samba_manager/backups"
    backup_file = os.path.join(backup_dir, filename)

    # Check if the file exists
    if not os.path.exists(backup_file):
        flash(f"Backup file {filename} not found", "error")
        return redirect("/backups")

    try:
        os.remove(backup_file)
        flash(f"Backup {filename} deleted successfully", "success")
    except Exception as e:
        flash(f"Failed to delete backup: {str(e)}", "error")

    return redirect("/backups")


@bp.route("/connections")
@login_required
def connections():
    """View active Samba connections"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to view connections", "error")
        return redirect("/")

    return render_template("connections.html", has_sudo=check_sudo_access())


@bp.route("/api/connections/terminate/<pid>", methods=["POST"])
@login_required
def api_terminate_connection(pid):
    """API endpoint to terminate a connection by PID"""
    if not check_sudo_access():
        return jsonify({"error": "Sudo access required to terminate connections"}), 403

    # Validate that PID is numeric
    try:
        pid_num = int(pid)
        if pid_num <= 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Invalid PID: {pid} - must be a positive number",
                    }
                ),
                400,
            )
    except ValueError:
        return (
            jsonify(
                {"success": False, "message": f"Invalid PID: {pid} - not a number"}
            ),
            400,
        )

    # Now use the numeric PID for termination
    success, message = terminate_connection(str(pid_num))

    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "message": message}), 400


@bp.route("/api/connections/terminate-machine/<machine>", methods=["POST"])
@login_required
def api_terminate_connection_by_machine(machine):
    """API endpoint to terminate all connections from a specific machine"""
    if not check_sudo_access():
        return jsonify({"error": "Sudo access required to terminate connections"}), 403

    # Validate machine name
    if not machine:
        return jsonify({"success": False, "message": "No machine name provided"}), 400

    success, message = terminate_connection_by_machine(machine)

    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "message": message}), 400


@bp.route("/disk-usage")
@login_required
def disk_usage():
    """View disk usage for shares"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to view disk usage", "error")
        return redirect("/")

    usage_stats = get_share_usage_stats()

    return render_template(
        "disk_usage.html", stats=usage_stats, has_sudo=check_sudo_access()
    )


@bp.route("/api/docs")
@login_required
def api_docs():
    """API documentation page"""
    return render_template("api_docs.html")


@bp.route("/enable", methods=["GET"])
@login_required
def enable_service():
    """Enable Samba services to start on boot"""
    if not check_sudo_access():
        flash("Error: Sudo access is required to enable Samba services", "error")
        return redirect("/setup")

    try:
        if DEV_MODE:
            flash("[DEV MODE] Would enable Samba services in production", "info")
        else:
            subprocess.run(["sudo", "systemctl", "enable", "smbd"], check=True)
            subprocess.run(["sudo", "systemctl", "enable", "nmbd"], check=True)
            flash("Samba services enabled to start on boot", "success")
    except Exception as e:
        flash(f"Failed to enable Samba services: {str(e)}", "error")

    return redirect("/setup")
