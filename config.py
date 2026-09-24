import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)

class Config:
    SECRET_KEY                  = os.getenv('SECRET_KEY', 'atss-secret-key')
    SQLALCHEMY_DATABASE_URI     = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'instance', 'timetable.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

MORNING_SLOTS = [
    (1, '7:30',  '8:25'),
    (2, '8:25',  '9:20'),
    (3, '9:30',  '10:25'),
    (4, '10:25', '11:20'),
    (5, '12:20', '1:15'),
    (6, '1:15',  '2:10'),
]

GENERAL_SLOTS = [
    (1, '9:30',  '10:25'),
    (2, '10:25', '11:20'),
    (3, '12:20', '1:15'),
    (4, '1:15',  '2:10'),
    (5, '2:30',  '3:25'),
    (6, '3:25',  '4:20'),
]

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

DESIGNATIONS  = ['Vice Principal', 'HOD', 'Associate Professor', 'Regular Faculty']
SHIFTS        = ['Morning', 'General']
SUBJECT_TYPES = ['Theory', 'Lab']
ROOM_TYPES    = ['Classroom', 'Lab', 'Seminar']

ODD_SEMESTERS  = [1, 3, 5, 7]
EVEN_SEMESTERS = [2, 4, 6]
SESSION_TYPES  = ['Odd', 'Even']   # Odd = sem 1,3,5,7 | Even = sem 2,4,6

DIVISIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
REQUESTED_COURSES = ['BSc IT', 'BCA', 'IMCA', 'MCA', 'MCA NEP', 'MSc IT', 'MSc IT NEP']
COURSE_ALIASES = {
    'BSc IT': 'BSc IT',
    'BSc IT Hons': 'BSc IT',
    'BCA': 'BCA',
    'BCA Hons': 'BCA',
}
NEP_RESTRICTED_COURSES = {'MCA NEP', 'MSc IT NEP'}
NEP_ALLOWED_SEMESTERS = {3, 4}
MIN_DAILY_LECTURES = 3
PREFERRED_DAILY_LECTURES = 3
MIN_DAILY_FREE_LECTURES = 1
MIN_SESSION_LECTURES = 3
MAX_DAILY_FREE_LECTURES = 2
DAILY_WORKING_SLOTS = 3
DAILY_THEORY_SLOTS = 3
DAILY_LAB_SLOTS = 1


def canonical_course(course):
    course = str(course or '').strip()
    return COURSE_ALIASES.get(course, course)


def is_requested_course(course):
    return canonical_course(course) in REQUESTED_COURSES


def is_course_semester_allowed(course, semester):
    course = canonical_course(course)
    return course not in NEP_RESTRICTED_COURSES or int(semester or 0) in NEP_ALLOWED_SEMESTERS

DESIGNATION_MAX_HOURS = {
    'Vice Principal':      6,
    'HOD':                12,
    'Associate Professor': 14,
    'Regular Faculty':    18,
}
