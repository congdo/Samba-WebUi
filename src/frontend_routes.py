from flask import send_from_directory

def register_frontend_routes(app):
    @app.route('/')
    def serve_index():
        return send_from_directory('frontend', 'index.html')

    @app.route('/frontend/<path:path>')
    def serve_frontend(path):
        return send_from_directory('frontend', path)