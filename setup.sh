#!/bin/bash

# Exit on any error
set -e

# Make sure we're root
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root"
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Uninstall function
uninstall() {
    echo "Uninstalling Samba WebUI..."

    # Remove from boot
    if command -v rc-update >/dev/null 2>&1; then
        rc-update del samba_webui default 2>/dev/null || true
    fi

    # Stop the service if running
    if [ -f "/etc/init.d/samba_webui" ]; then
        /etc/init.d/samba_webui stop 2>/dev/null || true
    fi

    # Remove files and directories
    rm -rf /opt/samba_webui
    rm -f /etc/init.d/samba_webui
    rm -rf /var/log/samba_webui
    rm -rf /var/lib/samba_webui
    rm -rf /run/samba_webui

    echo "Uninstallation complete!"
    exit 0
}

# Process command line arguments
if [ "$1" = "uninstall" ] || [ "$1" = "remove" ]; then
    uninstall
fi

echo "Installing Samba WebUI..."

# Create directories if they don't exist
echo "Creating directories..."
mkdir -p /opt/samba_webui
mkdir -p /var/log/samba_webui
mkdir -p /var/lib/samba_webui
mkdir -p /run/samba_webui

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
if ! command -v python3 -m venv &> /dev/null; then
    echo "Installing Python venv package..."
    if command -v apk &> /dev/null; then
        apk add python3-venv
    elif command -v apt-get &> /dev/null; then
        apt-get install -y python3-venv
    else
        echo "Could not install python3-venv. Please install it manually."
        exit 1
    fi
fi

python3 -m venv /opt/samba_webui/venv
source /opt/samba_webui/venv/bin/activate

# Install Python dependencies in virtual environment
echo "Installing Python dependencies..."
pip install --no-cache-dir flask flask-cors psutil PyJWT pexpect

# Copy source files
echo "Copying application files..."
if [ -d "${SCRIPT_DIR}/src" ]; then
    # Copy all non-JSON files first
    find "${SCRIPT_DIR}/src" -type f ! -name "*.json" -exec cp -r {} /opt/samba_webui/ \;
    
    # Create data directory for JSON files
    mkdir -p /var/lib/samba_webui
    
    # Only copy JSON files if they don't exist in destination
    if [ -f "${SCRIPT_DIR}/src/user_roles.json" ] && [ ! -f "/var/lib/samba_webui/user_roles.json" ]; then
        cp "${SCRIPT_DIR}/src/user_roles.json" /var/lib/samba_webui/
    fi
    if [ -f "${SCRIPT_DIR}/src/user_groups.json" ] && [ ! -f "/var/lib/samba_webui/user_groups.json" ]; then
        cp "${SCRIPT_DIR}/src/user_groups.json" /var/lib/samba_webui/
    fi
else
    echo "Error: Source directory not found at ${SCRIPT_DIR}/src"
    exit 1
fi

# Copy init script
echo "Installing init script..."
if [ -f "${SCRIPT_DIR}/initrc/samba_webui" ]; then
    cp "${SCRIPT_DIR}/initrc/samba_webui" /etc/init.d/samba_webui
    chmod 755 /etc/init.d/samba_webui
else
    echo "Error: Init script not found at ${SCRIPT_DIR}/initrc/samba_webui"
    exit 1
fi

# Create wrapper script to activate venv and run app
echo "Creating wrapper script..."
cat > /opt/samba_webui/run.sh << 'EOF'
#!/bin/bash

# Log file for this script
SCRIPT_LOG="/var/log/samba_webui/wrapper.log"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$SCRIPT_LOG"
}

# Ensure log directory exists
mkdir -p "$(dirname "$SCRIPT_LOG")"

log "Starting Samba WebUI wrapper script"

# Check virtual environment
if [ ! -f "/opt/samba_webui/venv/bin/activate" ]; then
    log "ERROR: Virtual environment not found at /opt/samba_webui/venv"
    exit 1
fi

# Change to application directory
cd /opt/samba_webui || {
    log "ERROR: Could not change to application directory"
    exit 1
}

# Activate virtual environment
log "Activating virtual environment"
source /opt/samba_webui/venv/bin/activate || {
    log "ERROR: Failed to activate virtual environment"
    exit 1
}

# Check if Python and required modules are available
log "Checking Python environment"
python3 -c "import flask, flask_cors, psutil" 2>> "$SCRIPT_LOG" || {
    log "ERROR: Missing required Python modules"
    exit 1
}

# Start the application
log "Starting application"
exec python app.py "$@" 2>&1 | tee -a "$SCRIPT_LOG"
EOF
chmod 755 /opt/samba_webui/run.sh

# Set permissions
echo "Setting permissions..."
chown -R root:root /opt/samba_webui
chmod 755 /opt/samba_webui
chmod 644 /opt/samba_webui/*.py
chmod 644 /opt/samba_webui/frontend/*
chmod 644 /opt/samba_webui/frontend/js/*
chmod -R 755 /opt/samba_webui/venv
chown -R root:root /var/lib/samba_webui
chmod 755 /var/lib/samba_webui
chmod 644 /var/lib/samba_webui/*.json 2>/dev/null || true
chmod 755 /run/samba_webui
chmod 755 /var/log/samba_webui

# Add to default runlevel
echo "Adding to default runlevel..."
if command -v rc-update >/dev/null 2>&1; then
    rc-update add samba_webui default
else
    echo "Warning: rc-update not found. Please manually configure service to start on boot."
fi

echo "Installation complete!"
echo
echo "File locations:"
echo "- Application: /opt/samba_webui/"
echo "- Virtual Environment: /opt/samba_webui/venv/"
echo "- Data: /var/lib/samba_webui/"
echo "- Logs: /var/log/samba_webui/"
echo "- Init script: /etc/init.d/samba_webui"
echo "- Runtime directory: /run/samba_webui/"
echo
echo "To uninstall: $0 uninstall"
echo
echo "Check logs at:"
echo "- Main log: /var/log/samba_webui/samba_webui.log"
echo "- Wrapper log: /var/log/samba_webui/wrapper.log"
echo
echo "Service commands:"
echo "    /etc/init.d/samba_webui start"
echo "    /etc/init.d/samba_webui stop"
echo "    /etc/init.d/samba_webui restart"
echo "    /etc/init.d/samba_webui status"