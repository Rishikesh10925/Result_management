"""Creates tables and demo accounts. Demo passwords are for local testing only."""
from models import Result, Student, User, db
from services import calculation_engine as ce
from services import result_service

DEMO_USERS = [
    ('admin', 'admin123', 'admin', 'Admin User', None),
    ('faculty', 'faculty123', 'faculty', 'Prof. Sharma', None),
    ('70572400001', 'student123', 'student', 'Aarav Patel', 3),    # CSDS, new scale
    ('70572200027', 'student123', 'student', 'Diya Rao', 2),       # CSDS, old scale
    ('70022500001', 'student123', 'student', 'Kabir Singh', 1),    # CE, new scale
]

# sem -> (ICA for every subject, TEE for TEE subjects)
DEMO_MARKS = {
    1: ([42, 38, 40, 35, 44, 45, 46, 40, 48], [78, 70, 66, 72, 80]),
    2: ([40, 41, 37, 39, 45, 44, 47, 42, 43], [74, 82, 60, 68, 76]),
}


def seed():
    db.create_all()
    for username, pw, role, name, sem in DEMO_USERS:
        if User.query.filter_by(username=username).first():
            continue
        user = User(username=username, name=name, role=role)
        user.set_password(pw)
        if role == 'student':
            _, category, department = ce.validate_sap_id(username)
            user.student = Student(sap_id=username, department=department, category=category, current_sem=sem)
        db.session.add(user)
    db.session.commit()

    for sap in ('70572400001', '70572200027'):
        student = Student.query.filter_by(sap_id=sap).first()
        for sem, (ica, tee) in DEMO_MARKS.items():
            if not Result.query.filter_by(student_id=student.id, sem=sem).first():
                result_service.save_marks_and_calculate(student, sem, ica, tee)
                Result.query.filter_by(student_id=student.id, sem=sem).first().published = True
    db.session.commit()
    print('Seeded. Logins: admin/admin123, faculty/faculty123, '
          '70572400001 | 70572200027 | 70022500001 / student123')


if __name__ == '__main__':
    from app import app
    with app.app_context():
        seed()
