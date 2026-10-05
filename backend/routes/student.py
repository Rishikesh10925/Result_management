from flask import Blueprint, Response, jsonify, request
from flask_login import current_user

from models import Result, db
from routes.common import audit, parse_sem, role_required
from services import calculation_engine as ce
from services import pdf_service, result_service, s3_service

bp = Blueprint('student', __name__, url_prefix='/api/student')


def me():
    return current_user.student


def published(sem):
    return Result.query.filter_by(student_id=me().id, sem=sem, published=True).first()


@bp.get('/results')
@role_required('student')
def results():
    rows = Result.query.filter_by(student_id=me().id, published=True).order_by(Result.sem).all()
    return jsonify([r.to_dict() for r in rows])


@bp.get('/results/<int:sem>')
@role_required('student')
def result_detail(sem):
    if not published(sem):
        return jsonify(error='Result not published yet.'), 404
    return jsonify(result_service.calculate(me(), sem))


@bp.get('/results/<int:sem>/pdf')
@role_required('student')
def result_pdf(sem):
    row = published(sem)
    if not row:
        return jsonify(error='Result not published yet.'), 404
    pdf = pdf_service.marksheet_pdf(current_user.name, me(), sem, result_service.calculate(me(), sem))
    key = s3_service.upload_pdf(f'marksheets/{me().sap_id}/sem{sem}.pdf', pdf)
    if key:
        row.pdf_key = key
        db.session.commit()
    audit(f'downloaded sem {sem} marksheet')
    return Response(pdf, mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename=ResultCloud_{me().sap_id}_sem{sem}.pdf'})


@bp.get('/layout/<int:sem>')
@role_required('student')
def layout(sem):
    return jsonify(result_service.semester_layout(me(), parse_sem(sem)))


@bp.post('/goal-matrix')
@role_required('student')
def goal_matrix():
    data = request.get_json(silent=True) or {}
    sem = parse_sem(data.get('sem'))
    tee_subjects = [s['subject'] for s in result_service.semester_layout(me(), sem) if s['has_tee']]
    ica = data.get('ica', [])
    if len(ica) != len(tee_subjects) or any(type(m) is not int or not 0 <= m <= 50 for m in ica):
        raise ValueError('Enter ICA marks (0-50) for every TEE subject.')
    low_marks, scale = ce.get_grade_config(me().category)
    return jsonify(subjects=tee_subjects, grades=list(scale.values()),
                   matrix=ce.calculate_goal_matrix(ica, low_marks))


@bp.post('/planner')
@role_required('student')
def planner():
    data = request.get_json(silent=True) or {}
    sem = parse_sem(data.get('sem'))
    s = me()
    exam_type, subjects, credits = ce.get_department_config(s.department)
    _, scale = ce.get_grade_config(s.category)
    subs = subjects[f'sem{sem}']
    levels = data.get('levels', [])
    if len(levels) != len(subs) or any(l not in ('easy', 'medium', 'hard') for l in levels):
        raise ValueError('Pick a difficulty for every subject.')
    target = float(data.get('target', 0))
    if not 0 <= target <= (4.0 if s.category == 'old' else 10.0):
        raise ValueError('Target GPA is out of range for your grading scale.')
    tee_count, ica_count = exam_type[f'sem{sem}']
    try:
        plans = ce.generate_multiple_plans(subs, target, levels, tee_count, ica_count,
                                           f'sem{sem}', s.category, scale, credits)
    except IndexError:
        raise ValueError(f'The reference logic cannot plan {s.department.upper()} semester {sem} (see README).')
    return jsonify(plans)
