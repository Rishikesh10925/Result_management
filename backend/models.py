import json
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)  # SAP ID for students
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # student / faculty / admin
    name = db.Column(db.String(100), nullable=False)
    student = db.relationship('Student', uselist=False, backref='user', cascade='all, delete-orphan')

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def to_dict(self):
        d = {'id': self.id, 'username': self.username, 'role': self.role, 'name': self.name}
        if self.student:
            d.update(self.student.to_dict())
        return d


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    sap_id = db.Column(db.String(11), unique=True, nullable=False)
    department = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(5), nullable=False)
    current_sem = db.Column(db.Integer, default=1)
    marks = db.relationship('Marks', backref='student', cascade='all, delete-orphan')
    results = db.relationship('Result', backref='student', cascade='all, delete-orphan')

    def to_dict(self):
        return {'student_id': self.id, 'sap_id': self.sap_id, 'department': self.department,
                'category': self.category, 'current_sem': self.current_sem}


class Marks(db.Model):
    __tablename__ = 'student_marks'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    sem = db.Column(db.Integer, nullable=False)
    ica_json = db.Column(db.Text, nullable=False)   # ICA of every subject, out of 50
    tee_json = db.Column(db.Text, nullable=False)   # TEE of TEE subjects, out of 100
    __table_args__ = (db.UniqueConstraint('student_id', 'sem'),)

    ica = property(lambda self: json.loads(self.ica_json))
    tee = property(lambda self: json.loads(self.tee_json))


class Result(db.Model):
    __tablename__ = 'semester_results'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    sem = db.Column(db.Integer, nullable=False)
    sgpa = db.Column(db.Float, nullable=False)
    cgpa = db.Column(db.Float)
    published = db.Column(db.Boolean, default=False)
    pdf_key = db.Column(db.String(255))  # S3 object key of the latest marksheet
    __table_args__ = (db.UniqueConstraint('student_id', 'sem'),)

    def to_dict(self):
        s = self.student
        return {'id': self.id, 'sem': self.sem, 'sgpa': self.sgpa, 'cgpa': self.cgpa,
                'published': self.published, 'pdf_key': self.pdf_key,
                'sap_id': s.sap_id, 'name': s.user.name}


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64))
    action = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'username': self.username, 'action': self.action,
                'time': self.created_at.strftime('%Y-%m-%d %H:%M')}
