from flask import Blueprint, jsonify, request

from models import AuditLog, Result, Student, User, db
from routes.common import audit, role_required
from services import calculation_engine as ce

bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@bp.get('/stats')
@role_required('admin')
def stats():
    return jsonify(students=Student.query.count(),
                   faculty=User.query.filter_by(role='faculty').count(),
                   results=Result.query.count(),
                   published=Result.query.filter_by(published=True).count())


@bp.get('/users')
@role_required('admin')
def users():
    q = User.query
    if request.args.get('role'):
        q = q.filter_by(role=request.args['role'])
    return jsonify([u.to_dict() for u in q.order_by(User.role, User.username).all()])


@bp.post('/users')
@role_required('admin')
def create_user():
    d = request.get_json(silent=True) or {}
    role, name, password = d.get('role'), str(d.get('name', '')).strip(), str(d.get('password', ''))
    if role not in ('student', 'faculty', 'admin') or not name or len(password) < 6:
        raise ValueError('Role, name and a password of at least 6 characters are required.')

    if role == 'student':
        sap_id = str(d.get('sap_id', '')).strip()
        ok, category, department = ce.validate_sap_id(sap_id)
        if not ok:
            raise ValueError('Invalid SAP ID.')
        username = sap_id
    else:
        username = str(d.get('username', '')).strip()
        if not username:
            raise ValueError('Username is required.')
    if User.query.filter_by(username=username).first():
        raise ValueError('That username / SAP ID already exists.')

    user = User(username=username, name=name, role=role)
    user.set_password(password)
    if role == 'student':
        user.student = Student(sap_id=sap_id, department=department, category=category,
                               current_sem=int(d.get('current_sem') or 1))
    db.session.add(user)
    db.session.commit()
    audit(f'created {role} {username}')
    return jsonify(user.to_dict()), 201


@bp.put('/users/<int:user_id>')
@role_required('admin')
def update_user(user_id):
    user = db.get_or_404(User, user_id)
    d = request.get_json(silent=True) or {}
    if d.get('name'):
        user.name = str(d['name']).strip()
    if d.get('password'):
        if len(d['password']) < 6:
            raise ValueError('Password must be at least 6 characters.')
        user.set_password(d['password'])
    if user.student and d.get('current_sem'):
        user.student.current_sem = int(d['current_sem'])
    db.session.commit()
    audit(f'updated {user.username}')
    return jsonify(user.to_dict())


@bp.delete('/users/<int:user_id>')
@role_required('admin')
def delete_user(user_id):
    user = db.get_or_404(User, user_id)
    db.session.delete(user)
    db.session.commit()
    audit(f'deleted {user.role} {user.username}')
    return jsonify(ok=True)


@bp.get('/results')
@role_required('admin')
def results():
    return jsonify([r.to_dict() for r in Result.query.order_by(Result.student_id, Result.sem).all()])


@bp.post('/results/<int:result_id>/publish')
@role_required('admin')
def publish(result_id):
    row = db.get_or_404(Result, result_id)
    row.published = bool((request.get_json(silent=True) or {}).get('published', True))
    db.session.commit()
    audit(f"{'published' if row.published else 'unpublished'} {row.student.sap_id} sem {row.sem}")
    return jsonify(row.to_dict())


@bp.get('/audit-logs')
@role_required('admin')
def audit_logs():
    return jsonify([a.to_dict() for a in AuditLog.query.order_by(AuditLog.id.desc()).limit(200).all()])


@bp.get('/config')
@role_required('admin')
def academic_config():
    # read-only view: the academic rules live in the calculation engine
    out = {}
    for dept in ('csds', 'ce'):
        exam, subjects, credits = ce.get_department_config(dept)
        out[dept] = {sem: {'subjects': subjects[sem], 'credits': credits[sem][:-1],
                           'total_credits': credits[sem][-1], 'exam_type': exam[sem]} for sem in subjects}
    return jsonify(out)
