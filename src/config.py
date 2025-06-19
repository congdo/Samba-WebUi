import os
import shutil

# Determine preferred user/group management tool
USE_ADDUSER = shutil.which("adduser") and not shutil.which("useradd")

# File paths
ROLES_FILE = "/var/lib/samba_webui/user_roles.json"
GROUPS_FILE = "/var/lib/samba_webui/user_groups.json"  # Now also stores master list of groups
SHARE_BASE_PATH = "/srv/samba"
SMB_CONF_PATH = "/etc/samba/smb.conf"

# Minimum GID for created custom/share groups (e.g., marketing, dev)
MIN_CUSTOM_GROUP_GID = 50000

# GIDs to explicitly ignore when finding the next available CUSTOM GID
CUSTOM_GIDS_TO_IGNORE = [65533, 65534]  # Common for 'nogroup', 'nobody'

# Minimum UID/GID for new user accounts (primary group will match this ID)
MIN_USER_UID_GID = 1000  # Standard starting point for regular user accounts