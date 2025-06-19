import os
import subprocess
import shutil
from utils import log, error
from user_management import group_exists_unix, user_exists_unix
from database import load_groups, save_groups, get_all_managed_groups
from config import MIN_CUSTOM_GROUP_GID, CUSTOM_GIDS_TO_IGNORE, SHARE_BASE_PATH

def get_next_available_custom_group_gid():
    """
    Finds the next available Group ID (GID) starting from MIN_CUSTOM_GROUP_GID.
    It will find the highest GID already assigned *at or above* MIN_CUSTOM_GROUP_GID,
    excluding GIDs specified in CUSTOM_GIDS_TO_IGNORE, and return 1 more than that.
    If no relevant GIDs exist, it returns MIN_CUSTOM_GROUP_GID.
    """
    highest_relevant_gid = MIN_CUSTOM_GROUP_GID - 1
    try:
        raw_groups = subprocess.check_output(['getent', 'group'], encoding='utf-8', stderr=subprocess.PIPE).splitlines()
        for line in raw_groups:
            parts = line.strip().split(':')
            if len(parts) >= 3 and parts[2].isdigit():
                current_gid = int(parts[2])

                if current_gid in CUSTOM_GIDS_TO_IGNORE:
                    continue

                if current_gid >= MIN_CUSTOM_GROUP_GID and current_gid > highest_relevant_gid:
                    highest_relevant_gid = current_gid
    except subprocess.CalledProcessError as e:
        error(f"Failed to get existing GIDs for custom groups: {e.stderr.decode().strip()}")
        return MIN_CUSTOM_GROUP_GID
    except FileNotFoundError:
        error("`getent` command not found. Cannot determine highest GID for custom groups.")
        return MIN_CUSTOM_GROUP_GID

    if highest_relevant_gid < MIN_CUSTOM_GROUP_GID:
        return MIN_CUSTOM_GROUP_GID
    else:
        return highest_relevant_gid + 1

def create_unix_group_and_share(groupname):
    """Create Unix group and associated share directory."""
    log(f"Creating Unix group and share for '{groupname}'...")
    if group_exists_unix(groupname):
        log(f"Group '{groupname}' already exists.")
        return True

    target_gid = get_next_available_custom_group_gid()

    try:
        log(f"Attempting to create Unix group '{groupname}' with GID {target_gid}...")
        subprocess.check_call(["groupadd", "-g", str(target_gid), groupname], stderr=subprocess.PIPE)
        log(f"Unix group '{groupname}' created with GID {target_gid}.")

        share_path = os.path.join(SHARE_BASE_PATH, groupname)
        os.makedirs(share_path, exist_ok=True)
        log(f"Created directory: {share_path}")
        subprocess.check_call(["chown", "-R", f":{groupname}", share_path], stderr=subprocess.PIPE)
        subprocess.check_call(["chmod", "g+rwx", share_path], stderr=subprocess.PIPE)
        subprocess.check_call(["chmod", "o-rwx", share_path], stderr=subprocess.PIPE)
        subprocess.check_call(["chmod", "g+s", share_path], stderr=subprocess.PIPE)  # Setgid bit for new files
        log(f"Set permissions for '{share_path}' to 770 and group to '{groupname}'.")

        groups_data = load_groups()
        if groupname not in groups_data["_groups"]:
            groups_data["_groups"].append(groupname)
            save_groups(groups_data)
            log(f"Group '{groupname}' added to groups database.")

        return True
    except (subprocess.CalledProcessError, OSError) as e:
        cmd_output = e.stderr.decode().strip() if hasattr(e, 'stderr') else str(e)
        error(f"Failed to create group or share for '{groupname}': {cmd_output}")
        groups_data = load_groups()
        if groupname in groups_data["_groups"]:
            groups_data["_groups"].remove(groupname)
            save_groups(groups_data)
        return False
    except FileNotFoundError as e:
        error(f"Command not found: {e}. Ensure necessary commands are in PATH and executable.")
        return False

def remove_unix_group_and_share(groupname):
    """Remove Unix group and its associated share directory."""
    log(f"Removing Unix group and share for '{groupname}'...")
    share_path = os.path.join(SHARE_BASE_PATH, groupname)
    success = True

    try:
        # 1. Remove group from all users in groups.json and their Unix groups
        groups_data = load_groups()
        users_to_update = [user for user, user_groups in groups_data.items() 
                          if user != "_groups" and groupname in user_groups]

        for user in users_to_update:
            if user_exists_unix(user):
                if not remove_user_from_unix_group(user, groupname):
                    error(f"Failed to remove user '{user}' from Unix group '{groupname}'. "
                          "Proceeding with group deletion.")
                    success = False
            if groupname in groups_data.get(user, []):
                groups_data[user].remove(groupname)
                log(f"Removed '{groupname}' from '{user}' in groups database.")

        # 2. Remove group from master list in groups.json
        if groupname in groups_data["_groups"]:
            groups_data["_groups"].remove(groupname)
        save_groups(groups_data)
        log(f"Group '{groupname}' removed from master list in groups database.")

        # 3. Remove Unix group
        if group_exists_unix(groupname):
            subprocess.check_call(["groupdel", groupname], stderr=subprocess.PIPE)
            log(f"Unix group '{groupname}' deleted.")
        else:
            log(f"Unix group '{groupname}' does not exist, skipping deletion.")

        # 4. Remove share directory
        if os.path.exists(share_path):
            shutil.rmtree(share_path)
            log(f"Share directory '{share_path}' removed.")
        else:
            log(f"Share directory '{share_path}' does not exist, skipping deletion.")

    except (subprocess.CalledProcessError, OSError) as e:
        cmd_output = e.stderr.decode().strip() if hasattr(e, 'stderr') else str(e)
        error(f"Failed to remove group '{groupname}': {cmd_output}")
        success = False
    except FileNotFoundError as e:
        error(f"Command not found: {e}. Ensure necessary commands are in PATH and executable.")
        success = False

    return success

def add_user_to_unix_group(username, groupname):
    """Add a Unix user to a group."""
    log(f"Adding Unix user '{username}' to group '{groupname}'...")
    try:
        subprocess.check_call(["usermod", "-aG", groupname, username], stderr=subprocess.PIPE)
        log(f"Successfully added '{username}' to group '{groupname}'.")
        return True
    except subprocess.CalledProcessError as e:
        error(f"Failed to add user '{username}' to group '{groupname}': {e.stderr.decode().strip()}")
        return False
    except FileNotFoundError as e:
        error(f"Command not found: {e}. Ensure `usermod` is in the PATH and executable.")
        return False

def remove_user_from_unix_group(username, groupname):
    """Remove a Unix user from a group."""
    log(f"Attempting to remove Unix user '{username}' from group '{groupname}'...")
    try:
        subprocess.check_call(["gpasswd", "-d", username, groupname], stderr=subprocess.PIPE)
        log(f"Successfully removed '{username}' from group '{groupname}'.")
        return True
    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.decode().strip() if e.stderr else f"Command exited with status {e.returncode}."
        if e.returncode == 3:  # User is not a member of the group
            log(f"User '{username}' is not a member of group '{groupname}' (gpasswd exit status 3). "
                "No action needed.")
            return True  # Consider it successful, as the desired state (not in group) is met.
        else:
            error(f"Failed to remove user '{username}' from group '{groupname}': {stderr_output}")
            return False
    except FileNotFoundError as e:
        error(f"Command not found: {e}. Ensure `gpasswd` is in the PATH and executable.")
        return False