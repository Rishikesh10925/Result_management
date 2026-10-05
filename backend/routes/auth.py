import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from models import User

bp = Blueprint('auth', __name__, url_prefix='/api/auth')
log = logging.getLogger(__name__)


@bp.post('/login')
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip()
    role = data.get('role')
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(str(data.get('password', ''))) or user.role != role:
        log.warning('failed login for %r as %s from %s', username, role, request.remote_addr)
        return jsonify(error='Invalid username, password or role.'), 401
    login_user(user)
    log.info('login %s (%s)', user.username, user.role)
    return jsonify(user.to_dict())


@bp.post('/logout')
@login_required
def logout():
    logout_user()
    return jsonify(ok=True)


@bp.get('/me')
def me():
    if not current_user.is_authenticated:
        return jsonify(error='Not logged in.'), 401
    return jsonify(current_user.to_dict())
