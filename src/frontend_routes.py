from flask import send_from_directory, jsonify
import subprocess

def register_frontend_routes(app):
    @app.route('/api/server-ip')
    def get_server_ip():
        try:
            # Run ip addr command and grep for eth0 IPv4 only (excluding IPv6)
            cmd = "ip addr show eth0 | grep -w 'inet' | awk '{print $2}' | cut -d'/' -f1"
            ip = subprocess.check_output(cmd, shell=True, text=True).strip()
            return jsonify({"ip": ip})
        except:
            return jsonify({"ip": "Could not determine IP address"})

    @app.route('/')
    def serve_index():
        return send_from_directory('frontend', 'index.html')

    @app.route('/frontend/<path:path>')
    def serve_frontend(path):
        return send_from_directory('frontend', path)