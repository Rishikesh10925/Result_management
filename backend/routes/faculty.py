from flask import Blueprint, jsonify, request

from models import Result, Student, User, db
from routes.common import audit, parse_sem, role_required
from services import result_service

bp = Blueprint('faculty', __name__, url_prefix='/api/faculty')


@bp.get('/students')
@role_required('faculty', 'admin')
def students():
    q = Student.query.join(User)
    if request.args.get('department'):
        q = q.filter(Student.department == request.args['department'])
    if request.args.get('search'):
        like = f"%{request.args['search']}%"
        q = q.filter(db.or_(User.name.like(like), Student.sap_id.like(like)))
    return jsonify([s.user.to_dict() for s in q.order_by(Student.sap_id).all()])


@bp.get('/marks/<int:student_id>/<int:sem>')
@role_required('faculty', 'admin')
def get_marks(student_id, sem):
    student = db.get_or_404(Student, student_id)
    sem = parse_sem(sem)
    res = result_service.calculate(student, sem)
    row = Result.query.filter_by(student_id=student_id, sem=sem).first()
    return jsonify(layout=result_service.semester_layout(student, sem), result=res,
                   published=bool(row and row.published))


@bp.post('/marks/<int:student_id>/<int:sem>')
@role_required('faculty', 'admin')
def save_marks(student_id, sem):
    student = db.get_or_404(Student, student_id)
    data = request.get_json(silent=True) or {}
    try:
        res = result_service.save_marks_and_calculate(student, parse_sem(sem), data.get('ica', []), data.get('tee', []))
    except ValueError:
        db.session.rollback()
        raise
    audit(f'saved marks for {student.sap_id} sem {sem}')
    return jsonify(res)


@bp.post('/results/<int:student_id>/<int:sem>/publish')
@role_required('faculty', 'admin')
def publish(student_id, sem):
    row = Result.query.filter_by(student_id=student_id, sem=sem).first_or_404()
    row.published = bool((request.get_json(silent=True) or {}).get('published', True))
    db.session.commit()
    audit(f"{'published' if row.published else 'unpublished'} {row.student.sap_id} sem {sem}")
    return jsonify(row.to_dict())
