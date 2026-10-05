"""Glue between the database and the calculation engine. No academic logic here."""
import json

from models import Marks, Result, db
from services import calculation_engine as ce


def semester_layout(student, sem):
    """Subjects of a semester, each marked as TEE or ICA-only."""
    exam_type, subjects, _ = ce.get_department_config(student.department)
    tee_count, ica_count = exam_type[f'sem{sem}']
    subs = subjects[f'sem{sem}'][:tee_count + ica_count]
    return [{'subject': s, 'has_tee': i < tee_count} for i, s in enumerate(subs)]


def previous_sgpas(student, sem):
    """SGPAs of sem 1..sem-1 from the database, or None if any is missing."""
    by_sem = {r.sem: r.sgpa for r in student.results}
    prev = [by_sem.get(n) for n in range(1, sem)]
    return None if None in prev else prev


def calculate(student, sem):
    marks = Marks.query.filter_by(student_id=student.id, sem=sem).first()
    if not marks:
        return None
    prev = previous_sgpas(student, sem)
    try:
        res = ce.calculate_result(student.sap_id, sem, marks.ica, marks.tee, prev or [])
    except IndexError:
        # reference behaviour: CE sem 2/3/4 have more subjects than CSDS credits
        raise ValueError(f'The reference logic cannot calculate {student.department.upper()} '
                         f'semester {sem} (credit table mismatch, see README).')
    if sem > 1 and prev is None:
        res['cgpa'] = None  # needs every previous semester's SGPA
    res['ica'], res['tee'] = marks.ica, marks.tee
    return res


def save_marks_and_calculate(student, sem, ica, tee):
    layout = semester_layout(student, sem)
    tee_count = sum(1 for s in layout if s['has_tee'])
    if len(ica) != len(layout) or len(tee) != tee_count:
        raise ValueError('Wrong number of marks for this semester.')
    if any(type(m) is not int or not 0 <= m <= 50 for m in ica):
        raise ValueError('ICA marks must be whole numbers from 0 to 50.')
    if any(type(m) is not int or not 0 <= m <= 100 for m in tee):
        raise ValueError('TEE marks must be whole numbers from 0 to 100.')

    marks = Marks.query.filter_by(student_id=student.id, sem=sem).first() or Marks(student_id=student.id, sem=sem)
    marks.ica_json, marks.tee_json = json.dumps(ica), json.dumps(tee)
    db.session.add(marks)
    db.session.flush()

    res = calculate(student, sem)
    row = Result.query.filter_by(student_id=student.id, sem=sem).first() or Result(student_id=student.id, sem=sem)
    row.sgpa, row.cgpa = res['sgpa'], res['cgpa']
    db.session.add(row)
    db.session.commit()
    return res
