from flask import jsonify, request
from utils import get_email_from_jwt, get_username_from_email, log, error
from config import MIN_USER_UID_GID
from database import (
    load_roles, save_roles, load_groups, save_groups,
    get_all_managed_groups, is_admin, get_user_status
)
from user_management import (
    user_exists_unix, samba_user_exists, create_unix_user,
    lock_user, unlock_user, group_exists_unix
)
from group_management import (
    create_unix_group_and_share, remove_unix_group_and_share,
    add_user_to_unix_group, remove_user_from_unix_group
)
from samba_config import generate_smb_conf, reload_samba
import subprocess
import shutil

def register_admin_routes(app):
    def admin_required(f):
        def wrapper(*args, **kwargs):
            email = get_email_from_jwt()
            if not is_admin(email):
                return jsonify({'error': 'Forbidden'}), 403
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper

    @app.route('/api/admin/users')
    @admin_required
    def get_users():
        roles = load_roles()
        groups_data = load_groups()
        all_managed_groups = get_all_managed_groups()

        all_display_usernames = set(roles.keys()).union(groups_data.keys())
        all_display_usernames.discard("_groups")

        system_users_raw = subprocess.check_output(["getent", "passwd"], encoding="utf-8", stderr=subprocess.PIPE).splitlines()
        for line in system_users_raw:
            parts = line.strip().split(":")
            if len(parts) >= 7:
                username, uid, shell = parts[0], int(parts[2]), parts[6]
                if uid >= MIN_USER_UID_GID and uid != 65534 and shell == "/sbin/nologin":
                    all_display_usernames.add(username)

        users = []
        for username in sorted(list(all_display_usernames)):
            # Only show supplementary groups, not the primary group (username)
            user_managed_groups = [g for g in groups_data.get(username, []) if g != username]
            groups_for_display = sorted(user_managed_groups)  # Don't include primary group
            
            # Exclude primary group from available groups
            available_groups_for_dropdown = sorted([
                g for g in all_managed_groups 
                if g not in user_managed_groups and g != username
            ])

            users.append({
                "username": username,
                "role": roles.get(username, "member"),
                "status": get_user_status(username),
                "groups": groups_for_display,
                "available_groups": available_groups_for_dropdown
            })

        return jsonify({'users': users})

    @app.route('/api/admin/groups')
    @admin_required
    def get_groups():
        return jsonify({'groups': get_all_managed_groups()})

    @app.route('/api/admin/users/import', methods=['POST'])
    @admin_required
    def import_users():
        data = request.get_json()
        if not data or 'import_data' not in data:
            return jsonify({'error': 'Missing import data'}), 400

        created_count = 0
        current_roles = load_roles()
        groups_data = load_groups()

        for u_email in data['import_data'].strip().splitlines():
            u = get_username_from_email(u_email.strip())
            if u and not user_exists_unix(u):
                if create_unix_user(u):
                    created_count += 1
                    current_roles[u] = "member"
                    groups_data[u] = []

        save_roles(current_roles)
        save_groups(groups_data)
        return jsonify({'message': f'Created {created_count} new users'})

    @app.route('/api/admin/groups/create', methods=['POST'])
    @admin_required
    def create_group():
        data = request.get_json()
        if not data or 'group_name' not in data:
            return jsonify({'error': 'Missing group name'}), 400

        new_group = data['group_name'].strip().lower()
        if not new_group:
            return jsonify({'error': 'Group name cannot be empty'}), 400

        all_managed_groups = get_all_managed_groups()
        if new_group in all_managed_groups:
            return jsonify({'error': f"Group '{new_group}' is already a managed group"}), 400

        if group_exists_unix(new_group):
            return jsonify({'error': f"Unix group '{new_group}' already exists but is not managed"}), 400

        if create_unix_group_and_share(new_group):
            if generate_smb_conf() and reload_samba():
                return jsonify({'message': f"Group '{new_group}' and share created successfully"})
            return jsonify({'error': f"Group '{new_group}' created, but Samba update failed"}), 500
        return jsonify({'error': f"Failed to create group '{new_group}'"}), 500

    @app.route('/api/admin/groups/delete', methods=['POST'])
    @admin_required
    def delete_group():
        data = request.get_json()
        if not data or 'group_name' not in data:
            return jsonify({'error': 'Missing group name'}), 400

        group_name = data['group_name']
        all_managed_groups = get_all_managed_groups()
        if group_name not in all_managed_groups:
            return jsonify({'error': f"Group '{group_name}' is not a managed group"}), 400

        if remove_unix_group_and_share(group_name):
            if generate_smb_conf() and reload_samba():
                return jsonify({'message': f"Group '{group_name}' removed successfully"})
            return jsonify({'error': f"Group '{group_name}' removed, but Samba update failed"}), 500
        return jsonify({'error': f"Failed to remove group '{group_name}'"}), 500

    @app.route('/api/admin/users/toggle-admin', methods=['POST'])
    @admin_required
    def toggle_admin():
        data = request.get_json()
        if not data or 'username' not in data:
            return jsonify({'error': 'Missing username'}), 400

        username = data['username']
        current_roles = load_roles()
        current_role = current_roles.get(username, "member")
        new_role = "member" if current_role == "admin" else "admin"
        current_roles[username] = new_role
        save_roles(current_roles)
        
        return jsonify({'message': f"User '{username}' role changed to '{new_role}'"})

    @app.route('/api/admin/users/toggle-disable', methods=['POST'])
    @admin_required
    def toggle_disable():
        data = request.get_json()
        if not data or 'username' not in data:
            return jsonify({'error': 'Missing username'}), 400

        username = data['username']
        current_roles = load_roles()
        current_role = current_roles.get(username, "member")

        if current_role == "disabled":
            current_roles[username] = "member"
            if unlock_user(username):
                save_roles(current_roles)
                return jsonify({'message': f"User '{username}' enabled"})
            return jsonify({'error': f"Failed to enable user '{username}'"}), 500
        else:
            current_roles[username] = "disabled"
            if lock_user(username):
                save_roles(current_roles)
                return jsonify({'message': f"User '{username}' disabled"})
            return jsonify({'error': f"Failed to disable user '{username}'"}), 500

    @app.route('/api/admin/users/delete', methods=['POST'])
    @admin_required
    def delete_user():
        data = request.get_json()
        if not data or 'username' not in data:
            return jsonify({'error': 'Missing username'}), 400

        username = data['username']
        try:
            if samba_user_exists(username):
                subprocess.check_call(["smbpasswd", "-x", username], stderr=subprocess.PIPE)

            if shutil.which("userdel"):
                subprocess.check_call(["userdel", "-r", username], stderr=subprocess.PIPE)
            elif shutil.which("deluser"):
                subprocess.check_call(["deluser", "--remove-home", username], stderr=subprocess.PIPE)

            if group_exists_unix(username):
                try:
                    log(f"Attempting to delete user's primary group '{username}'...")
                    subprocess.check_call(["groupdel", username], stderr=subprocess.PIPE)
                    log(f"User's primary group '{username}' deleted.")
                except Exception as groupdel_e:
                    error(f"Failed to delete user's primary group '{username}': {groupdel_e}")

            current_roles = load_roles()
            groups_data = load_groups()
            current_roles.pop(username, None)
            groups_data.pop(username, None)
            save_roles(current_roles)
            save_groups(groups_data)

            if generate_smb_conf() and reload_samba():
                return jsonify({'message': f"User '{username}' deleted successfully"})
            return jsonify({'error': f"User deleted but Samba update failed"}), 500

        except Exception as e:
            error_msg = e.stderr.decode().strip() if hasattr(e, 'stderr') else str(e)
            error(f"Failed to delete user: {error_msg}")
            return jsonify({'error': f"Error deleting user '{username}': {error_msg}"}), 500

    @app.route('/api/admin/users/add-to-group', methods=['POST'])
    @admin_required
    def add_to_group():
        data = request.get_json()
        if not data or 'username' not in data or 'group_name' not in data:
            return jsonify({'error': 'Missing username or group name'}), 400

        username = data['username']
        group_name = data['group_name']
        groups_data = load_groups()
        current_user_groups = groups_data.get(username, [])
        all_managed_groups = get_all_managed_groups()

        if group_name in current_user_groups:
            return jsonify({'error': f"User '{username}' is already in group '{group_name}'"}), 400

        if group_name not in all_managed_groups or not user_exists_unix(username):
            return jsonify({'error': f"User or group does not exist or is not managed"}), 400

        if add_user_to_unix_group(username, group_name):
            current_user_groups.append(group_name)
            groups_data[username] = sorted(current_user_groups)
            save_groups(groups_data)
            
            if generate_smb_conf() and reload_samba():
                return jsonify({'message': f"User '{username}' added to group '{group_name}'"})
            return jsonify({'error': 'User added to group but Samba update failed'}), 500
        return jsonify({'error': 'Failed to add user to Unix group'}), 500

    @app.route('/api/admin/users/remove-from-group', methods=['POST'])
    @admin_required
    def remove_from_group():
        data = request.get_json()
        if not data or 'username' not in data or 'group_name' not in data:
            return jsonify({'error': 'Missing username or group name'}), 400

        username = data['username']
        group_name = data['group_name']
        groups_data = load_groups()
        current_user_groups = groups_data.get(username, [])
        all_managed_groups = get_all_managed_groups()

        if group_name not in current_user_groups:
            return jsonify({'error': f"User '{username}' is not in group '{group_name}'"}), 400

        if group_name not in all_managed_groups or not user_exists_unix(username):
            return jsonify({'error': f"User or group does not exist or is not managed"}), 400

        if remove_user_from_unix_group(username, group_name):
            current_user_groups.remove(group_name)
            groups_data[username] = sorted(current_user_groups)
            save_groups(groups_data)
            
            if generate_smb_conf() and reload_samba():
                return jsonify({'message': f"User removed from group '{group_name}'"})
            return jsonify({'error': 'User removed from group but Samba update failed'}), 500
        return jsonify({'error': 'Failed to remove user from Unix group'}), 500