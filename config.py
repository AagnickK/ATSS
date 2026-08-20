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
