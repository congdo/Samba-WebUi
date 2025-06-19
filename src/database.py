import os
import json
from utils import log
from config import ROLES_FILE, GROUPS_FILE

def load_roles():
    """Load user roles from json file."""
    if os.path.exists(ROLES_FILE):
        with open(ROLES_FILE) as f:
            log(f"Loading roles from {ROLES_FILE}")
            return json.load(f)
    log(f"No existing roles file at {ROLES_FILE}, creating empty roles")
    return {}

def save_roles(roles):
    """Save user roles to json file."""
    with open(ROLES_FILE, "w") as f:
        log(f"Saving roles to {ROLES_FILE}")
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
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE) as f:
            log(f"Loading groups from {GROUPS_FILE}")
            data = json.load(f)
            # Ensure _groups key exists
            if "_groups" not in data:
                data["_groups"] = []
            return data
    log(f"No existing groups file at {GROUPS_FILE}, creating empty groups")
    return {"_groups": []}  # Initialize with an empty master group list

def save_groups(groups_data):
    """Save groups data to json file."""
    with open(GROUPS_FILE, "w") as f:
        log(f"Saving groups to {GROUPS_FILE}")
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