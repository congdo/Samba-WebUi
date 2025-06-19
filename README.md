# Samba Web UI

> **⚠️ Security Notice**: This application has no built-in security measures as it relies entirely on Cloudflare for security. We trust Cloudflare to generate and validate JWT tokens, and to only allow users with valid JWTs to access the application. All security is handled at the Cloudflare level.

> **📝 Development Note**: This project was primarily developed by AI with human guidance and oversight. The codebase, documentation, and architecture were created through collaborative interaction between AI and human developers.

A Flask web application for managing Samba users and shares.

## Project Structure
```
samba_webui/
├── src/                    # Application source code
│   ├── app.py             # Main application
│   ├── config.py          # Configuration
│   ├── database.py        # Data management
│   ├── user_management.py # User operations
│   ├── group_management.py # Group operations
│   ├── frontend/          # Frontend files
│   │   ├── index.html
│   │   ├── admin.html
│   │   └── js/
│   └── ...
├── initrc/
│   └── samba_webui        # OpenRC init script
└── setup.sh               # Installation script
```

## Installation

```bash
# Clone this repository
git clone https://github.com/yourusername/samba_webui.git
cd samba_webui

# Install
sudo chmod +x setup.sh
sudo ./setup.sh
```

The setup script will:
- Install the application to `/opt/samba_webui/`
- Create and configure Python virtual environment
- Set up init scripts in `/etc/init.d/`
- Create necessary directories and set permissions
- Install Python dependencies in the virtual environment
- Add the service to the default runlevel

## Service Management

Control the service using standard OpenRC commands:
```bash
# Start the service
sudo /etc/init.d/samba_webui start

# Stop the service
sudo /etc/init.d/samba_webui stop

# Restart the service
sudo /etc/init.d/samba_webui restart

# Check service status
sudo /etc/init.d/samba_webui status
```

The service will automatically start on boot.

## Uninstallation

To completely remove the application:
```bash
sudo ./setup.sh uninstall
# or
sudo ./setup.sh remove
```

This will:
- Stop the service
- Remove it from boot sequence
- Delete all application files and directories
- Remove logs and data
- Clean up runtime files

## Development

To run in development mode:
```bash
# Activate the virtual environment
source /opt/samba_webui/venv/bin/activate

# Change to application directory
cd /opt/samba_webui

# Run the application
python app.py
```

Development mode features:
- Runs on port 8888 (production uses 8080)
- Shows database file locations
- Displays full API documentation
- Enables debug mode
- Provides verbose logging

## File Locations

- Application: `/opt/samba_webui/`
- Virtual Environment: `/opt/samba_webui/venv/`
- Data: `/var/lib/samba_webui/`
- Logs: `/var/log/samba_webui/`
- Init script: `/etc/init.d/samba_webui`
- Runtime files: `/run/samba_webui/`
- Wrapper script: `/opt/samba_webui/run.sh`

## Requirements

The setup script will automatically install:
- python3-venv (for virtual environment)
- Flask (web framework)
- Flask-CORS (for CORS support)
- psutil (for process management)
- PyJWT (for JWT handling)

## API Endpoints

All API endpoints are prefixed with `/api/`

### User Endpoints
- GET `/api/user/profile` - Get current user profile
- POST `/api/user/password` - Update user password

### Admin Endpoints
- GET `/api/admin/users` - List all users
- GET `/api/admin/groups` - List all groups
- POST `/api/admin/users/import` - Bulk import users
- POST `/api/admin/groups/create` - Create new group
- POST `/api/admin/groups/delete` - Delete group
- POST `/api/admin/users/toggle-admin` - Toggle user admin status
- POST `/api/admin/users/toggle-disable` - Toggle user enabled/disabled status
- POST `/api/admin/users/delete` - Delete user
- POST `/api/admin/users/add-to-group` - Add user to group
- POST `/api/admin/users/remove-from-group` - Remove user from group

## Features

- User Management:
  - Create/delete Samba users
  - Enable/disable user accounts
  - Change user passwords
  - Manage user roles (admin/member)

- Group Management:
  - Create/delete groups with associated shares
  - Add/remove users from groups
  - Automatic Samba share configuration

- Security:
  - JWT-based authentication
  - Role-based access control
  - Secure password management