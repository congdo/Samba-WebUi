import os
import json
from utils import log

def _get_json_path():
    """Return dictionary of JSON database file paths."""
    script_dir = os.path.dirname(os.path.realpath(__file__))
    return {
        'roles': os.path.join(script_dir, 'user_roles.json'),
        'groups': os.path.join(script_dir, 'user_groups.json')
    }

def load_roles():
    """Load user roles from json file."""
    json_paths = _get_json_path()
    roles_file = json_paths['roles']
    if os.path.exists(roles_file):
        with open(roles_file) as f:
            log(f"Loading roles from {roles_file}")
            return json.load(f)
    log(f"No existing roles file at {roles_file}, creating empty roles")
    return {}

def save_roles(roles):
    """Save user roles to json file."""
    json_paths = _get_json_path()
    roles_file = json_paths['roles']
    with open(roles_file, "w") as f:
        log(f"Saving roles to {roles_file}")
        json.dump(roles, f, indent=2)

def load_groups():
    """
    Loads group data. The structure will be:
    {
        "_groups": ["group1", "group2", ...], # Master list of all groups created/managed
        "user1": ["group1", "group3"],
        "user2": ["group2"],
        ...
    }
    """
    json_paths = _get_json_path()
    groups_file = json_paths['groups']
    if os.path.exists(groups_file):
        with open(groups_file) as f:
            log(f"Loading groups from {groups_file}")
            data = json.load(f)
            # Ensure _groups key exists
            if "_groups" not in data:
                data["_groups"] = []
            return data
    log(f"No existing groups file at {groups_file}, creating empty groups")
    return {"_groups": []}  # Initialize with an empty master group list

def save_groups(groups_data):
    """Save groups data to json file."""
    json_paths = _get_json_path()
    groups_file = json_paths['groups']
    with open(groups_file, "w") as f:
        log(f"Saving groups to {groups_file}")
        json.dump(groups_data, f, indent=2)

def get_all_managed_groups():
    """Returns a sorted list of all group names managed by the application."""
    groups_data = load_groups()
    return sorted(list(set(groups_data.get("_groups", []))))  # Use set for uniqueness

def is_admin(email):
    """Check if user has admin role."""
    from utils import get_username_from_email
    if email == "cong.do@mozox.com":
        return True
    roles = load_roles()
    username = get_username_from_email(email)
    return roles.get(username) == "admin"

def get_user_status(username):
    """Get user's enabled/disabled status."""
    roles = load_roles()
    return "Disabled" if roles.get(username) == "disabled" else "Enabled"