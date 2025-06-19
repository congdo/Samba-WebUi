import os
import pwd
import subprocess
import psutil
from flask import Flask
from flask_cors import CORS

from config import SHARE_BASE_PATH
from utils import log, error
from user_management import group_exists_unix
from samba_config import generate_smb_conf, reload_samba
from frontend_routes import register_frontend_routes
from user_routes import register_user_routes
from admin_routes import register_admin_routes
from database import _get_json_path

def is_running_from_rc():
    """Check if the process is being run from an RC script."""
    try:
        current_process = psutil.Process()
        while True:
            parent = current_process.parent()
            if parent is None:
                break
            if parent.name().startswith('openrc') or parent.name() == 'init':
                return True
            current_process = parent
        return False
    except:
        return False

def create_app():
    app = Flask(__name__, static_folder='frontend')
    CORS(app)
    app.secret_key = os.urandom(24)

    # Register route modules
    register_frontend_routes(app)
    register_user_routes(app)
    register_admin_routes(app)

    return app

def init_system():
    """Initialize system requirements."""
    # Initial setup for smbuser group
    if not group_exists_unix("smbuser"):
        log("Creating base 'smbuser' group...")
        try:
            subprocess.check_call(["groupadd", "smbuser"], stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            error(f"Failed to create 'smbuser' group: {e.stderr.decode().strip()}.")
        except FileNotFoundError as e:
            error(f"Command not found: {e}. Ensure `groupadd` is in the PATH.")

    # Create and set permissions for share base directory
    os.makedirs(SHARE_BASE_PATH, exist_ok=True)
    try:
        current_user = os.environ.get('USER')
        if not current_user:
            current_user = pwd.getpwuid(os.geteuid()).pw_name

        subprocess.check_call(["chown", current_user, SHARE_BASE_PATH], stderr=subprocess.PIPE)
        subprocess.check_call(["chmod", "755", SHARE_BASE_PATH], stderr=subprocess.PIPE)
        log(f"Set permissions for {SHARE_BASE_PATH}: owner={current_user}, mode=755")
    except Exception as e:
        error(f"Warning: Could not set owner/permissions for {SHARE_BASE_PATH}: {e}")

    # Initial Samba configuration
    if generate_smb_conf():
        reload_samba()
        log("Samba configuration generated and service reloaded successfully")
    else:
        error("Initial smb.conf generation failed.")

if __name__ == "__main__":
    # Initialize system requirements
    init_system()

    # Create and run the application
    app = create_app()
    
    # Determine settings based on how the script is running
    is_rc = is_running_from_rc()
    host = "0.0.0.0"  # Always bind to all interfaces
    port = 8080 if is_rc else 8888  # Use 8888 for development mode
    debug = not is_rc  # Enable debug mode when running from command line
    
    if debug:
        # Show database file locations
        json_paths = _get_json_path()
        log("\nJSON Database Locations:")
        log(f"  Roles DB: {json_paths['roles']}")
        log(f"  Groups DB: {json_paths['groups']}")
        
        log("\nRunning in development mode with debug enabled")
        log(f"Access the application at http://{host}:{port}")
        log("\nAPI Documentation:")
        log("  - GET     /api/user/profile            Get current user profile")
        log("  - POST    /api/user/password          Update user password")
        log("  - GET     /api/admin/users            List all users")
        log("  - GET     /api/admin/groups           List all groups")
        log("  - POST    /api/admin/users/import     Bulk import users")
        log("  - POST    /api/admin/groups/create    Create new group")
        log("  - POST    /api/admin/groups/delete    Delete group")
        log("  - POST    /api/admin/users/toggle-admin    Toggle user admin status")
        log("  - POST    /api/admin/users/toggle-disable  Toggle user enabled/disabled status")
        log("  - POST    /api/admin/users/delete     Delete user")
        log("  - POST    /api/admin/users/add-to-group    Add user to group")
        log("  - POST    /api/admin/users/remove-from-group  Remove user from group")
        log("\nNote: Development server running on port 8888 while production runs on 8080")
    else:
        log("Running in production mode")
    
    log(f"Starting server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)