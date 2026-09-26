"""
Excel importer — reads Faculty_Teaching_Allocation_Schedule.xlsx
and populates Faculty, Subject, Division, Allocation tables.
"""
import pandas as pd
from extensions import db
from models import Faculty, Subject, Division, Allocation
from config import ODD_SEMESTERS, DESIGNATION_MAX_HOURS, canonical_course, is_course_semester_allowed


def _session_type(semester):
    return 'Odd' if int(semester or 0) in ODD_SEMESTERS else 'Even'


def _max_hours(designation, excel_value):
    """Use designation cap from config; fall back to Excel value if designation unknown."""
    return DESIGNATION_MAX_HOURS.get(str(designation).strip(), int(excel_value or 18))

def import_faculty_excel(filepath):
    df = pd.read_excel(filepath)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    faculty_records = Faculty.query.all()
    faculty_by_id = {faculty.faculty_id: faculty for faculty in faculty_records if faculty.faculty_id}
    faculty_by_name = {faculty.name: faculty for faculty in faculty_records}
    subjects_by_key = {
        (subject.subject_name, subject.course, subject.semester): subject
        for subject in Subject.query.all()
    }
    divisions_by_key = {
        (division.course, division.semester, division.division): division
        for division in Division.query.all()
    }
    allocation_keys = set(
        db.session.query(Allocation.faculty_id, Allocation.subject_id, Allocation.division_id).all()
    )

    added = 0
    for _, row in df.iterrows():
        name = str(row.get('faculty_name', row.get('name', ''))).strip()
        if not name or name == 'nan':
            continue

        fac_id = str(row.get('faculty_id', '')).strip()
        # Match by faculty_id tag first (FAC-1001), fall back to name
        if fac_id and fac_id != 'nan':
            faculty = faculty_by_id.get(fac_id)
        else:
            faculty = faculty_by_name.get(name)

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
            if faculty.faculty_id:
                faculty_by_id[faculty.faculty_id] = faculty
            faculty_by_name[faculty.name] = faculty
            added += 1

        # Subject columns: subject_name, course, semester, type, lecture_hours, lab_hours
        sub_name = str(row.get('subject_name', row.get('subject', ''))).strip()
        course   = canonical_course(row.get('course', ''))
        semester = int(row.get('semester', 0) or 0)
        if not is_course_semester_allowed(course, semester):
            continue
        if sub_name and sub_name != 'nan':
            subject_key = (sub_name, course, semester)
            subject = subjects_by_key.get(subject_key)
            if not subject:
                sem      = semester
                sub_type = str(row.get('type', 'Theory')).strip()
                subject = Subject(
                    subject_name  = sub_name,
                    course        = course,
                    semester      = sem,
                    session_type  = _session_type(sem),
                    type          = sub_type,
                    lecture_hours = int(row.get('lecture_hours', 3) or 3) if sub_type == 'Theory' else 0,
                    lab_hours     = int(row.get('lab_hours', 0) or 0)     if sub_type == 'Lab'    else 0,
                )
                db.session.add(subject)
                db.session.flush()
                subjects_by_key[subject_key] = subject

            # Division expansion rules:
            #   IMCA           -> div A only
            #   all others     -> divs A-I
            # The course rule is authoritative, even when Excel has a
            # division column, so every course receives its complete set.
            from config import DIVISIONS
            if course == 'IMCA':
                div_list = ['A']
            else:
                div_list = DIVISIONS   # A-I

            for div in div_list:
                division_key = (course, semester, div)
                division = divisions_by_key.get(division_key)
                if not division:
                    division = Division(
                        course       = course,
                        semester     = semester,
                        division     = div,
                        students     = int(row.get('students', 60) or 60),
                        shift        = str(row.get('shift', 'General')).strip(),
                        session_type = _session_type(semester),
                    )
                    db.session.add(division)
                    db.session.flush()
                    divisions_by_key[division_key] = division

                allocation_key = (faculty.id, subject.id, division.id)
                if allocation_key not in allocation_keys:
                    db.session.add(Allocation(
                        faculty_id=faculty.id,
                        subject_id=subject.id,
                        division_id=division.id,
                    ))
                    allocation_keys.add(allocation_key)

    db.session.commit()
    return added
