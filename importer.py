"""
Excel importer — reads Faculty_Teaching_Allocation_Schedule.xlsx
and populates Faculty, Subject, Division, Allocation tables.
"""
import pandas as pd
from extensions import db
from models import Faculty, Subject, Division, Allocation
from config import ODD_SEMESTERS


def _session_type(semester):
    return 'Odd' if int(semester or 0) in ODD_SEMESTERS else 'Even'


_DESIGNATION_MAX = {
    'Vice Principal':      6,
    'HOD':                12,
    'Associate Professor': 14,
    'Regular Faculty':    18,
}

def _max_hours(designation, excel_value):
    """Use designation cap; fall back to Excel value if designation unknown."""
    return _DESIGNATION_MAX.get(str(designation).strip(), int(excel_value or 18))

def import_faculty_excel(filepath):
    df = pd.read_excel(filepath)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    added = 0
    for _, row in df.iterrows():
        name = str(row.get('faculty_name', row.get('name', ''))).strip()
        if not name or name == 'nan':
            continue

        fac_id = str(row.get('faculty_id', '')).strip()
        # Match by faculty_id tag first (FAC-1001), fall back to name
        if fac_id and fac_id != 'nan':
            faculty = Faculty.query.filter_by(faculty_id=fac_id).first()
        else:
            faculty = Faculty.query.filter_by(name=name).first()

        if not faculty:
            faculty = Faculty(
                faculty_id  = fac_id if fac_id and fac_id != 'nan' else None,
                name        = name,
                designation = str(row.get('designation', '')).strip(),
                department  = str(row.get('department', '')).strip(),
                shift       = str(row.get('shift', 'General')).strip(),
                max_hours   = _max_hours(row.get('designation', ''), row.get('max_hours', 18)),
                email       = str(row.get('email', '')).strip(),
            )
            db.session.add(faculty)
            db.session.flush()
            added += 1

        # Subject columns: subject_name, course, semester, type, lecture_hours, lab_hours
        sub_name = str(row.get('subject_name', row.get('subject', ''))).strip()
        if sub_name and sub_name != 'nan':
            subject = Subject.query.filter_by(
                subject_name=sub_name,
                course=str(row.get('course', '')).strip(),
                semester=int(row.get('semester', 0) or 0),
            ).first()
            if not subject:
                sem = int(row.get('semester', 0) or 0)
                subject = Subject(
                    subject_name  = sub_name,
                    course        = str(row.get('course', '')).strip(),
                    semester      = sem,
                    session_type  = _session_type(sem),
                    type          = str(row.get('type', 'Theory')).strip(),
                    lecture_hours = int(row.get('lecture_hours', 3) or 3),
                    lab_hours     = int(row.get('lab_hours', 0) or 0),
                )
                db.session.add(subject)
                db.session.flush()

            div_name = str(row.get('division', 'A')).strip()
            course   = str(row.get('course', '')).strip()
            semester = int(row.get('semester', 0) or 0)
            division = Division.query.filter_by(
                course=course, semester=semester, division=div_name
            ).first()
            if not division:
                division = Division(
                    course       = course,
                    semester     = semester,
                    division     = div_name,
                    students     = int(row.get('students', 60) or 60),
                    shift        = str(row.get('shift', 'General')).strip(),
                    session_type = _session_type(semester),
                )
                db.session.add(division)
                db.session.flush()

            exists = Allocation.query.filter_by(
                faculty_id=faculty.id,
                subject_id=subject.id,
                division_id=division.id,
            ).first()
            if not exists:
                db.session.add(Allocation(
                    faculty_id=faculty.id,
                    subject_id=subject.id,
                    division_id=division.id,
                ))

    db.session.commit()
    return added
