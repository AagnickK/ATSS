from flask_login import UserMixin
from extensions import db


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(50), unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(256), nullable=False)
    role       = db.Column(db.String(20), default='admin')   # admin | faculty | student


class Faculty(db.Model):
    __tablename__ = 'faculty'
    id          = db.Column(db.Integer, primary_key=True)
    faculty_id  = db.Column(db.String(20), unique=True, nullable=True)  # e.g. FAC-1001
    name        = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(50))
    department  = db.Column(db.String(50))
    shift       = db.Column(db.String(20))
    max_hours   = db.Column(db.Integer, default=18)
    email       = db.Column(db.String(120))

    allocations = db.relationship('Allocation', backref='faculty', lazy=True)
    timetable   = db.relationship('Timetable', backref='faculty', lazy=True)


class Subject(db.Model):
    __tablename__ = 'subject'
    id            = db.Column(db.Integer, primary_key=True)
    subject_name  = db.Column(db.String(100), nullable=False)
    course        = db.Column(db.String(50))
    semester      = db.Column(db.Integer)
    session_type  = db.Column(db.String(10))   # Odd | Even (auto-derived from semester)
    type          = db.Column(db.String(20))   # Theory | Lab
    lecture_hours = db.Column(db.Integer, default=0)
    lab_hours     = db.Column(db.Integer, default=0)

    allocations   = db.relationship('Allocation', backref='subject', lazy=True)
    timetable     = db.relationship('Timetable', backref='subject', lazy=True)


class Division(db.Model):
    __tablename__ = 'division'
    id           = db.Column(db.Integer, primary_key=True)
    course       = db.Column(db.String(50))
    semester     = db.Column(db.Integer)
    division     = db.Column(db.String(10))
    students     = db.Column(db.Integer, default=0)
    shift        = db.Column(db.String(20))
    session_type = db.Column(db.String(10))   # Odd | Even (auto-derived from semester)

    allocations = db.relationship('Allocation', backref='division', lazy=True)
    timetable   = db.relationship('Timetable', backref='division', lazy=True)


class Room(db.Model):
    __tablename__ = 'room'
    id       = db.Column(db.Integer, primary_key=True)
    room_no  = db.Column(db.String(20), unique=True, nullable=False)
    type     = db.Column(db.String(20))   # Classroom | Lab | Seminar
    capacity = db.Column(db.Integer, default=30)
    building = db.Column(db.String(50))

    timetable = db.relationship('Timetable', backref='room', lazy=True)


class Allocation(db.Model):
    """Faculty → Subject → Division assignment"""
    __tablename__ = 'allocation'
    id         = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    division_id= db.Column(db.Integer, db.ForeignKey('division.id'), nullable=False)


class Timetable(db.Model):
    __tablename__ = 'timetable'
    id         = db.Column(db.Integer, primary_key=True)
    day        = db.Column(db.String(20), nullable=False)
    slot       = db.Column(db.Integer, nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'))
    division_id= db.Column(db.Integer, db.ForeignKey('division.id'))
    room_id    = db.Column(db.Integer, db.ForeignKey('room.id'))
    batch      = db.Column(db.String(10), nullable=True)   # A1, A2, A3 for lab batches
    locked     = db.Column(db.Boolean, default=False)
