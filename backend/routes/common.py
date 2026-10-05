from functools import wraps

from flask import jsonify
from flask_login import current_user

from models import AuditLog, db


def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify(error='Please log in.'), 401
            if current_user.role not in roles:
                return jsonify(error='You do not have access to this page.'), 403
            return fn(*args, **kwargs)
        return wrapper
    return deco


def audit(action):
    db.session.add(AuditLog(username=current_user.username, action=action))
    db.session.commit()


def parse_sem(value):
    try:
        sem = int(value)
    except (TypeError, ValueError):
        sem = 0
    if not 1 <= sem <= 8:
        raise ValueError('Semester must be 1 to 8.')
    return sem
