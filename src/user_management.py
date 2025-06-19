import subprocess
import shutil
from utils import log, error
from config import USE_ADDUSER, MIN_USER_UID_GID

def user_exists_unix(username):
    """Check if Unix user exists."""
    try:
        subprocess.check_output(["id", username], stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        error("`id` command not found. Ensure it's in the PATH.")
        return False

def samba_user_exists(username):
    """Check if Samba user exists."""
    try:
        output = subprocess.check_output(["pdbedit", "-L"], encoding="utf-8", stderr=subprocess.PIPE)
        return any(line.startswith(f"{username}:") for line in output.splitlines())
    except subprocess.CalledProcessError as e:
        error(f"Failed to check Samba users (pdbedit): {e.stderr.decode().strip()}")
        return False
    except FileNotFoundError:
        error("`pdbedit` command not found. Ensure it's in the PATH.")
        return False

def get_next_available_uid_gid_pair():
    """
    Finds the smallest available integer >= MIN_USER_UID_GID that is not
    currently used as a UID or a GID on the system.
    """
    used_uids = set()
    used_gids = set()

    try:
        raw_passwd = subprocess.check_output(['getent', 'passwd'], encoding='utf-8', stderr=subprocess.PIPE).splitlines()
        for line in raw_passwd:
            parts = line.strip().split(':')
            if len(parts) >= 3 and parts[2].isdigit():
                used_uids.add(int(parts[2]))

        raw_groups = subprocess.check_output(['getent', 'group'], encoding='utf-8', stderr=subprocess.PIPE).splitlines()
        for line in raw_groups:
            parts = line.strip().split(':')
            if len(parts) >= 3 and parts[2].isdigit():
                used_gids.add(int(parts[2]))

    except subprocess.CalledProcessError as e:
        error(f"Failed to get existing UIDs/GIDs: {e.stderr.decode().strip()}")
        return MIN_USER_UID_GID
    except FileNotFoundError:
        error("`getent` command not found. Cannot determine existing UIDs/GIDs.")
        return MIN_USER_UID_GID  # Fallback

    current_id = MIN_USER_UID_GID
    # Add a safety break to prevent infinite loops if something goes wrong
    max_search_id = 65535  # Standard upper bound for regular users/groups
    while current_id <= max_search_id:
        if current_id not in used_uids and current_id not in used_gids:
            return current_id
        current_id += 1

    error(f"Could not find a unique UID/GID pair below {max_search_id + 1}. Returning next available high ID.")
    # Fallback if no suitable ID found in the desired range
    return max(max(used_uids) if used_uids else 0, max(used_gids) if used_gids else 0) + 1

def create_unix_user(username):
    """Create a Unix user with matching primary group and home directory."""
    log(f"Creating Unix user '{username}' (with matching primary group and home directory)...")

    id_to_assign = get_next_available_uid_gid_pair()
    log(f"Assigning UID/GID: {id_to_assign} for user '{username}'.")

    try:
        if not group_exists_unix(username):
            log(f"Creating primary group '{username}' with GID {id_to_assign}...")
            subprocess.check_call(["groupadd", "-g", str(id_to_assign), username], stderr=subprocess.PIPE)
            log(f"Primary group '{username}' created with GID {id_to_assign}.")
        else:
            log(f"Primary group '{username}' already exists. Skipping group creation.")

        if USE_ADDUSER:
            subprocess.check_call(["adduser", "-m", "-u", str(id_to_assign), "-s", "/sbin/nologin", "-g", username, username], stderr=subprocess.PIPE)
        else:
            subprocess.check_call(["useradd", "-m", "-u", str(id_to_assign), "-s", "/sbin/nologin", "-g", username, username], stderr=subprocess.PIPE)

        log(f"Unix user '{username}' created with UID {id_to_assign}, primary group '{username}' (GID {id_to_assign}) and home directory.")

        return True
    except subprocess.CalledProcessError as e:
        error(f"Failed to create Unix user or primary group: {e.stderr.decode().strip()}")
        if user_exists_unix(username):
            log(f"Cleaning up partially created user '{username}'...")
            try:
                if shutil.which("userdel"): 
                    subprocess.check_call(["userdel", "-r", username], stderr=subprocess.PIPE)
                elif shutil.which("deluser"): 
                    subprocess.check_call(["deluser", "--remove-home", username], stderr=subprocess.PIPE)
            except Exception as cleanup_e:
                error(f"Failed to clean up user '{username}': {cleanup_e}")

        if group_exists_unix(username):
            log(f"Cleaning up partially created primary group '{username}'...")
            try:
                subprocess.check_call(["groupdel", username], stderr=subprocess.PIPE)
            except Exception as cleanup_e:
                error(f"Failed to clean up primary group '{username}': {cleanup_e}")
        return False
    except FileNotFoundError as e:
        error(f"Command not found: {e}. Ensure `groupadd`, `adduser`/`useradd` are in the PATH and executable.")
        return False

def change_password(username, new_password):
    """Change or set Samba password for a user."""
    import pexpect
    log(f"Starting password update or creation for '{username}'...")
    if not user_exists_unix(username):
        error(f"Cannot change password for non-existent user '{username}'.")
        return False
    try:
        command = f"smbpasswd -a {username}" if not samba_user_exists(username) else f"smbpasswd {username}"
        log(f"Executing: {command}")
        child = pexpect.spawn(command, encoding='utf-8', timeout=10)
        child.expect("New SMB password:", timeout=5)
        child.sendline(new_password)
        child.expect("Retype new SMB password:", timeout=5)
        child.sendline(new_password)
        child.expect(pexpect.EOF, timeout=5)
        output = child.before
        # Consider success if there's no error message, even with "Forcing Primary Group"
        if ("Added user" in output or
            "Changed password" in output or
            ("Forcing Primary Group" in output and "failed" not in output.lower())):
            log(f"Samba password for '{username}' set successfully.")
            return True
        else:
            log(f"Samba password command output: {output}")
            return False
    except pexpect.exceptions.TIMEOUT:
        error(f"Samba password command timed out for '{username}'. Output so far: {child.before}")
        return False
    except pexpect.exceptions.EOF:
        error(f"Samba password command finished unexpectedly for '{username}'. Output: {child.before}")
        return False
    except Exception as e:
        error(f"Exception during Samba password handling for '{username}': {e}")
        return False

def lock_user(username):
    """Lock Unix user and disable Samba account."""
    log(f"Locking Unix user '{username}' and disabling Samba account...")
    try:
        subprocess.check_call(["usermod", "-L", username], stderr=subprocess.PIPE)
        subprocess.check_call(["smbpasswd", "-d", username], stderr=subprocess.PIPE)
        log(f"User '{username}' locked.")
        return True
    except subprocess.CalledProcessError as e:
        error(f"Failed to lock user '{username}': {e.stderr.decode().strip()}")
        return False
    except FileNotFoundError as e:
        error(f"Command not found: {e}. Ensure `usermod` and `smbpasswd` are in the PATH.")
        return False

def unlock_user(username):
    """Unlock Unix user and enable Samba account."""
    log(f"Unlocking Unix user '{username}' and enabling Samba account...")
    try:
        subprocess.check_call(["usermod", "-U", username], stderr=subprocess.PIPE)
        subprocess.check_call(["smbpasswd", "-e", username], stderr=subprocess.PIPE)
        log(f"User '{username}' unlocked.")
        return True
    except subprocess.CalledProcessError as e:
        error(f"Failed to unlock user '{username}': {e.stderr.decode().strip()}")
        return False
    except FileNotFoundError as e:
        error(f"Command not found: {e}. Ensure `usermod` and `smbpasswd` are in the PATH.")
        return False

def group_exists_unix(groupname):
    """Check if Unix group exists."""
    try:
        subprocess.check_output(["getent", "group", groupname], stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        error("`getent` command not found. Ensure it's in the PATH.")
        return False