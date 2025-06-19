from flask import jsonify, request
from utils import get_email_from_jwt, get_username_from_email
from database import load_roles, is_admin
from user_management import user_exists_unix, create_unix_user, change_password

def register_user_routes(app):
    @app.route('/api/user/profile')
    def get_profile():
        email = get_email_from_jwt()
        if not email:
            return jsonify({'error': 'Unauthorized'}), 401

        username = get_username_from_email(email)
        if not username:
            return jsonify({'error': 'Invalid token'}), 401

        roles = load_roles()
        if roles.get(username) == "disabled":
            return jsonify({'error': 'Account is disabled'}), 403

        return jsonify({
            'username': username,
            'email': email,
            'is_admin': is_admin(email)
        })

    @app.route('/api/user/password', methods=['POST'])
    def update_password():
        email = get_email_from_jwt()
        if not email:
            return jsonify({'error': 'Unauthorized'}), 401

        username = get_username_from_email(email)
        if not username:
            return jsonify({'error': 'Invalid token'}), 401

        data = request.get_json()
        if not data or 'password' not in data:
            return jsonify({'error': 'Missing password'}), 400

        if not user_exists_unix(username):
            create_unix_user(username)

        if change_password(username, data['password']):
            return jsonify({'message': 'Password changed successfully'})
        return jsonify({'error': 'Failed to change password'}), 500