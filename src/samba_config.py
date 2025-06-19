import os
import subprocess
import shutil
from utils import log, error
from database import get_all_managed_groups
from user_management import group_exists_unix
from config import SHARE_BASE_PATH, SMB_CONF_PATH

def generate_smb_conf():
    """Generate Samba configuration file."""
    log("Generating smb.conf...")

    all_managed_groups = get_all_managed_groups()

    config_lines = [
        "[global]",
        "   log level = 3",
        "   #to allow symlinks from everywhere",
        "   allow insecure wide links = yes",
        "   workgroup = WORKGROUP",
        "   dos charset = cp866",
        "   unix charset = utf-8",
        "   security = user",
        "   server string = MozoX NAS Server",
        "",
        "[mozox]",
        "   # to follow symlinks",
        "   follow symlinks = yes",
        "   # to allow symlinks from outside",
        "   wide links = yes",
        "   browseable = yes",
        "   writeable = yes",
        f"   path = {SHARE_BASE_PATH}/mozox",
        "   force user = smb",
        "",
        "[homes]",
        "   comment = Home Directories",
        "   browseable = no",
        "   writable = yes",
        "   valid users = %S",
        "",
    ]

    for group_name in sorted(all_managed_groups):
        share_path = os.path.join(SHARE_BASE_PATH, group_name)
        if os.path.isdir(share_path) and group_exists_unix(group_name):
            config_lines.extend([
                f"[{group_name}]",
                f"   path = {share_path}",
                f"   workgroup = {group_name}",
                f"   force group = {group_name}",
                "   create mask = 0660",
                "   directory mask = 0770",
                "   read only = no",
                "   guest ok = no",
                "   browseable = yes",
                ""
            ])

    try:
        with open(SMB_CONF_PATH, "w") as f:
            f.write("\n".join(config_lines))
        log(f"smb.conf successfully generated at {SMB_CONF_PATH}")
        return True
    except IOError as e:
        error(f"Failed to write smb.conf: {e}")
        return False

def reload_samba():
    """Reload Samba service to apply configuration changes."""
    log("Reloading Samba service...")
    try:
        if shutil.which("systemctl"):
            subprocess.check_call(["systemctl", "reload", "smbd", "nmbd"], stderr=subprocess.PIPE)
        elif shutil.which("/etc/init.d/samba"):
            subprocess.check_call(["/etc/init.d/samba", "reload"], stderr=subprocess.PIPE)
        else:
            error("Neither systemctl nor /etc/init.d/samba found for reloading Samba.")
            return False
        log("Samba service reloaded successfully.")
        return True
    except subprocess.CalledProcessError as e:
        error(f"Failed to reload Samba service: {e.stderr.decode().strip()}")
        return False
    except FileNotFoundError as e:
        error(f"Command not found: {e}. Ensure `systemctl` or `/etc/init.d/samba` is in the PATH.")
        return False