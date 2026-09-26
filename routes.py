from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify, send_file, current_app, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy import or_, update
from sqlalchemy.orm import selectinload
from extensions import db, bcrypt
from models import User, Faculty, Subject, Division, Room, Allocation, Timetable, TimetableRevision
from config import DAYS, MORNING_SLOTS, GENERAL_SLOTS, DESIGNATIONS, SHIFTS, SUBJECT_TYPES, ROOM_TYPES, SESSION_TYPES, ODD_SEMESTERS, EVEN_SEMESTERS, DIVISIONS, REQUESTED_COURSES, DESIGNATION_MAX_HOURS, COURSE_ALIASES, canonical_course, is_requested_course, is_course_semester_allowed
import otp as otp_module

# ── Auth Blueprint ────────────────────────────────────────────────────────────
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if not otp_module.is_configured():
            flash('Gmail not configured in .env', 'error')
            return render_template('register.html')
        username = request.form['username']
        email    = request.form['email']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html')
        code = otp_module.generate_otp()
        try:
            otp_module.send_otp(email, code)
        except Exception as e:
            flash(f'Failed to send OTP: {e}', 'error')
            return render_template('register.html')
        session['pending_user'] = {
            'username': username,
            'email':    email,
            'password': bcrypt.generate_password_hash(password).decode('utf-8'),
        }
        session['otp_code']  = code
        session['otp_email'] = email
        return redirect(url_for('auth.verify_otp'))
    return render_template('register.html')

@auth.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = session.get('otp_email', '')
    if not email:
        return redirect(url_for('auth.register'))
    if request.method == 'POST':
        if request.form.get('otp', '').strip() == session.get('otp_code'):
            pending = session.pop('pending_user', None)
            session.pop('otp_code', None)
            if pending:
                db.session.add(User(
                    username=pending['username'],
                    email=pending['email'],
                    password=pending['password'],
                ))
                db.session.commit()
                flash('Account created! Please log in.', 'success')
                return redirect(url_for('auth.login'))
        else:
            flash('Incorrect OTP.', 'error')
    return render_template('verify_otp.html', email=email)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


# ── Main Blueprint ────────────────────────────────────────────────────────────
main = Blueprint('main', __name__)

@main.route('/documentation/')
def documentation():
    return send_from_directory(current_app.config['ATSS_DOC_DIR'], 'index.html')

@main.route('/documentation/<path:filename>')
def documentation_asset(filename):
    return send_from_directory(current_app.config['ATSS_DOC_DIR'], filename)

@main.route('/')
def index():
    return redirect(url_for('auth.login'))

@main.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'faculty':   Faculty.query.count(),
        'subjects':  Subject.query.count(),
        'divisions': Division.query.count(),
        'rooms':     Room.query.count(),
        'entries':   Timetable.query.count(),
    }
    return render_template('dashboard.html', stats=stats)


# ── Faculty Blueprint ─────────────────────────────────────────────────────────
faculty_bp = Blueprint('faculty_bp', __name__)

@faculty_bp.route('/faculty')
@login_required
def faculty_list():
    faculty = Faculty.query.order_by(Faculty.name).all()
    return render_template('faculty.html', faculty=faculty,
                           designations=DESIGNATIONS, shifts=SHIFTS)

@faculty_bp.route('/faculty/add', methods=['POST'])
@login_required
def faculty_add():
    designation = request.form['designation']
    db.session.add(Faculty(
        name        = request.form['name'],
        designation = designation,
        department  = request.form['department'],
        shift       = request.form['shift'],
        max_hours   = DESIGNATION_MAX_HOURS.get(designation, int(request.form.get('max_hours', 18))),
        email       = request.form.get('email', ''),
    ))
    db.session.commit()
    flash('Faculty added.', 'success')
    return redirect(url_for('faculty_bp.faculty_list'))

@faculty_bp.route('/faculty/delete/<int:fid>', methods=['POST'])
@login_required
def faculty_delete(fid):
    Faculty.query.filter_by(id=fid).delete()
    db.session.commit()
    flash('Faculty removed.', 'success')
    return redirect(url_for('faculty_bp.faculty_list'))

@faculty_bp.route('/faculty/template')
@login_required
def faculty_template():
    import io, openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Faculty Import'
    headers = [
        'faculty_id', 'faculty_name', 'designation', 'department', 'shift',
        'max_hours', 'email', 'subject_name', 'course', 'semester',
        'type', 'lecture_hours', 'lab_hours', 'students'
    ]
    hdr_fill = PatternFill('solid', fgColor='FF9000')
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color='18181B')
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal='center')
        ws.column_dimensions[cell.column_letter].width = max(len(h) + 4, 14)
    samples = [
        # VP — General, Theory
        ['FAC-1001', 'Dr. V. Principal',  'Vice Principal',      'Computer Science', 'General',  6,
         'vp@college.edu',        'Research Methodology', 'MCA',         1, 'Theory', 3, 0, 40],
        # HOD — General, Theory + Lab
        ['FAC-1002', 'Dr. A. Kumar',      'HOD',                 'Computer Science', 'General', 12,
         'hod1@college.edu',      'Data Structures',      'BSc IT',      1, 'Theory', 3, 0, 60],
        ['FAC-1002', 'Dr. A. Kumar',      'HOD',                 'Computer Science', 'General', 12,
         'hod1@college.edu',      'Data Structures Lab',  'BSc IT',      1, 'Lab',    0, 2, 60],
        # Associate Professor — General, Theory + Lab
        ['FAC-1006', 'Dr. E. Mehta',      'Associate Professor', 'Information Technology', 'General', 14,
         'ap1@college.edu',       'DBMS',                 'BCA',         3, 'Theory', 3, 0, 60],
        ['FAC-1006', 'Dr. E. Mehta',      'Associate Professor', 'Information Technology', 'General', 14,
         'ap1@college.edu',       'DBMS Lab',             'BCA',         3, 'Lab',    0, 2, 60],
        # Regular — General, various courses
        ['FAC-1011', 'Prof. Amit Sharma', 'Regular Faculty',     'Computer Science', 'General', 18,
         'fac11@college.edu',     'Discrete Mathematics', 'BSc IT Hons', 1, 'Theory', 3, 0, 60],
        ['FAC-1012', 'Prof. Priya Verma', 'Regular Faculty',     'Information Technology', 'General', 18,
         'fac12@college.edu',     'Mathematics I',        'BCA Hons',    1, 'Theory', 3, 0, 60],
        ['FAC-1013', 'Prof. Rahul Gupta', 'Regular Faculty',     'Computer Science', 'General', 18,
         'fac13@college.edu',     'Mathematics I',        'IMCA',        1, 'Theory', 3, 0, 60],
        # Regular — Morning, PG courses
        ['FAC-1015', 'Prof. Vijay Patel', 'Regular Faculty',     'Information Technology', 'Morning', 18,
         'fac15@college.edu',     'Advanced Algorithms',  'MCA',         1, 'Theory', 3, 0, 40],
        ['FAC-1016', 'Prof. Anita Mehta', 'Regular Faculty',     'Computer Science', 'Morning', 18,
         'fac16@college.edu',     'Advanced Algorithms',  'MCA NEP',     1, 'Theory', 3, 0, 40],
        ['FAC-1017', 'Prof. Suresh Joshi','Regular Faculty',     'Information Technology', 'Morning', 18,
         'fac17@college.edu',     'Advanced Mathematics', 'MSc IT',      1, 'Theory', 3, 0, 40],
        ['FAC-1018', 'Prof. Kavita Rao',  'Regular Faculty',     'Computer Science', 'Morning', 18,
         'fac18@college.edu',     'Advanced Mathematics', 'MSc IT NEP',  1, 'Theory', 3, 0, 40],
        ['FAC-1015', 'Prof. Vijay Patel', 'Regular Faculty',     'Information Technology', 'Morning', 18,
         'fac15@college.edu',     'Advanced Algorithms Lab', 'MCA',      1, 'Lab',    0, 2, 40],
    ]
    for row in samples:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, download_name='faculty_import_template.xlsx',
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@faculty_bp.route('/faculty/import', methods=['POST'])
@login_required
def faculty_import():
    from importer import import_faculty_excel
    import io
    f = request.files.get('excel')
    if not f or not f.filename:
        flash('No file selected.', 'error')
        return redirect(url_for('faculty_bp.faculty_list'))
    buf = io.BytesIO(f.read())
    added = import_faculty_excel(buf)
    flash(f'Imported {added} faculty records.', 'success')
    return redirect(url_for('faculty_bp.faculty_list'))


# ── Subjects Blueprint ────────────────────────────────────────────────────────
subject_bp = Blueprint('subject_bp', __name__)

@subject_bp.route('/subjects')
@login_required
def subject_list():
    subjects = Subject.query.order_by(Subject.course, Subject.semester).all()
    return render_template('subjects.html', subjects=subjects, types=SUBJECT_TYPES)

@subject_bp.route('/subjects/add', methods=['POST'])
@login_required
def subject_add():
    sem = int(request.form.get('semester', 1))
    db.session.add(Subject(
        subject_name  = request.form['subject_name'],
        course        = request.form['course'],
        semester      = sem,
        session_type  = 'Odd' if sem in ODD_SEMESTERS else 'Even',
        type          = request.form['type'],
        lecture_hours = int(request.form.get('lecture_hours', 0)),
        lab_hours     = int(request.form.get('lab_hours', 0)),
    ))
    db.session.commit()
    flash('Subject added.', 'success')
    return redirect(url_for('subject_bp.subject_list'))

@subject_bp.route('/subjects/delete/<int:sid>', methods=['POST'])
@login_required
def subject_delete(sid):
    Subject.query.filter_by(id=sid).delete()
    db.session.commit()
    flash('Subject removed.', 'success')
    return redirect(url_for('subject_bp.subject_list'))


# ── Rooms Blueprint ───────────────────────────────────────────────────────────
room_bp = Blueprint('room_bp', __name__)

@room_bp.route('/rooms')
@login_required
def room_list():
    rooms = Room.query.order_by(Room.room_no).all()
    return render_template('classroom.html', rooms=rooms, types=ROOM_TYPES)

@room_bp.route('/rooms/add', methods=['POST'])
@login_required
def room_add():
    db.session.add(Room(
        room_no  = request.form['room_no'],
        type     = request.form['type'],
        capacity = int(request.form.get('capacity', 30)),
        building = request.form.get('building', ''),
    ))
    db.session.commit()
    flash('Room added.', 'success')
    return redirect(url_for('room_bp.room_list'))

@room_bp.route('/rooms/delete/<int:rid>', methods=['POST'])
@login_required
def room_delete(rid):
    Room.query.filter_by(id=rid).delete()
    db.session.commit()
    flash('Room removed.', 'success')
    return redirect(url_for('room_bp.room_list'))


# ── Timetable Blueprint ───────────────────────────────────────────────────────
tt_bp = Blueprint('tt_bp', __name__)


def _timetable_display_options():
    return (
        selectinload(Timetable.faculty).load_only(Faculty.name),
        selectinload(Timetable.subject).load_only(Subject.subject_name, Subject.type),
        selectinload(Timetable.division).load_only(
            Division.course, Division.semester, Division.division, Division.session_type,
        ),
        selectinload(Timetable.room).load_only(Room.room_no),
    )


def _requested_timetable_export_rows():
    payload = request.get_json(silent=True)
    rows = payload.get('rows') if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return None

    columns = ('day', 'slot', 'faculty', 'subject', 'division', 'room', 'batch')
    if any(not isinstance(row, dict) for row in rows):
        return None
    return [[str(row.get(column) or '') for column in columns] for row in rows]


def _current_timetable_revision():
    db.session.execute(
        update(TimetableRevision)
        .where(TimetableRevision.id == 1, TimetableRevision.pending.is_(True))
        .values(
            revision=TimetableRevision.revision + 1,
            pending=False,
        )
    )
    revision = db.session.query(TimetableRevision.revision).filter_by(id=1).scalar()
    db.session.commit()
    return revision


@tt_bp.route('/timetable')
@login_required
def timetable_view():
    divisions  = Division.query.order_by(Division.course, Division.semester, Division.division).all()
    faculty    = Faculty.query.order_by(Faculty.name).all()
    courses    = sorted({canonical_course(d.course) for d in divisions if d.course})
    sel_div    = request.args.get('division_id', type=int)
    sel_fac    = request.args.get('faculty_id',  type=int)
    sel_session = request.args.get('session_type', '')   # 'Odd' | 'Even' | ''
    cache_scope = f"{sel_session if sel_session in ('Odd', 'Even') else 'all'}:{sel_div or 0}:{sel_fac or 0}"
    cache_revision = _current_timetable_revision()
    cache_token = f'{cache_revision}:{cache_scope}'
    cache_current = request.cookies.get('timetable_revision') == cache_token

    query = Timetable.query
    if sel_session in ('Odd', 'Even'):
        sems = ODD_SEMESTERS if sel_session == 'Odd' else EVEN_SEMESTERS
        matching_division_ids = [
            division.id for division in divisions
            if division.semester in sems
            and is_requested_course(division.course)
            and is_course_semester_allowed(division.course, division.semester)
        ]
        query = query.filter(Timetable.division_id.in_(matching_division_ids))
    if sel_div:
        query = query.filter(Timetable.division_id == sel_div)
    if sel_fac:
        query = query.filter(Timetable.faculty_id == sel_fac)

    entries = [] if cache_current else query.options(*_timetable_display_options()).all()

    return render_template('timetable.html',
                           entries=entries, days=DAYS,
                           morning_slots=MORNING_SLOTS, general_slots=GENERAL_SLOTS,
                           divisions=divisions, faculty=faculty, courses=courses,
                           course_aliases=COURSE_ALIASES,
                           sel_div=sel_div, sel_fac=sel_fac,
                           sel_session=sel_session, session_types=SESSION_TYPES,
                           cache_scope=cache_scope, cache_revision=cache_revision,
                           cache_token=cache_token, cache_current=cache_current)


@tt_bp.route('/timetable/revision')
@login_required
def timetable_revision():
    return jsonify({'revision': _current_timetable_revision()})

@tt_bp.route('/timetable/generate', methods=['POST'])
@login_required
def timetable_generate():
    from scheduler import generate_timetable
    session_type = request.form.get('session_type', '').strip()   # 'Odd' | 'Even'

    # Must be exactly Odd or Even — no blank/all allowed
    if session_type not in ('Odd', 'Even'):
        flash('Please select a session (Odd or Even) before generating.', 'error')
        return redirect(url_for('tt_bp.timetable_view'))

    sems = ODD_SEMESTERS if session_type == 'Odd' else EVEN_SEMESTERS

    all_divisions = Division.query.all()
    semester_division_ids = [d.id for d in all_divisions if d.semester in sems]
    locked_entries = (
        Timetable.query
        .join(Timetable.division)
        .filter(or_(
            Timetable.locked.is_(True),
            Division.semester.is_(None),
            Division.semester.notin_(sems),
        ))
        .all()
    )

    # Clear only unlocked entries for this session in one indexed DELETE.
    Timetable.query.filter(
        Timetable.locked.is_(False),
        Timetable.division_id.in_(semester_division_ids),
    ).delete(synchronize_session=False)
    db.session.commit()

    session_divisions = [
        d for d in all_divisions
        if d.semester in sems and is_requested_course(d.course)
        and is_course_semester_allowed(d.course, d.semester)
    ]
    present_courses = {canonical_course(d.course) for d in session_divisions}
    missing_courses = [course for course in REQUESTED_COURSES if course not in present_courses]
    missing_divisions = []
    course_semesters = {(canonical_course(d.course), d.semester) for d in session_divisions}
    for course, semester in sorted(course_semesters):
        expected = ['A'] if course == 'IMCA' else DIVISIONS
        course_sem_divisions = {
            d.division for d in session_divisions
            if canonical_course(d.course) == course and d.semester == semester
        }
        missing = [name for name in expected if name not in course_sem_divisions]
        if missing:
            missing_divisions.append(
                f'{course} Sem{semester}: {", ".join(missing)}'
            )

    allocations = Allocation.query.filter(
        Allocation.division_id.in_([d.id for d in session_divisions])
    ).all()
    total_allocations = Allocation.query.count()
    allocated_division_ids = {a.division_id for a in allocations}
    missing_allocations = [
        f'{d.course} Sem{d.semester} {d.division}'
        for d in session_divisions
        if canonical_course(d.course) in REQUESTED_COURSES and d.id not in allocated_division_ids
    ]
    faculty_map  = {f.id: f for f in Faculty.query.all()}
    subject_map  = {s.id: s for s in Subject.query.all()}
    division_map = {d.id: d for d in session_divisions}
    room_list    = Room.query.all()

    # Only schedule allocations for the selected session. Some allocations
    # belong to the other session and therefore are intentionally absent from
    # division_map.
    available_allocations = [
        a for a in allocations
        if a.division_id in division_map
    ]
    ignored_allocations = total_allocations - len(available_allocations)
    allocations = available_allocations

    entries, shortages = generate_timetable(
        allocations, faculty_map, subject_map, division_map, room_list,
        reserved_entries=locked_entries,
        return_diagnostics=True,
    )
    for e in entries:
        db.session.add(Timetable(**e))
    db.session.commit()
    if ignored_allocations:
        flash(
            f'Data notice — {ignored_allocations} allocations belong to the other session '
            'or have no matching division and were skipped.',
            'warning',
        )
    if missing_courses or missing_divisions or missing_allocations:
        details = []
        if missing_courses:
            details.append(f'missing courses: {", ".join(missing_courses)}')
        if missing_divisions:
            details.append(f'missing divisions: {", ".join(missing_divisions[:5])}')
            if len(missing_divisions) > 5:
                details.append(f'and {len(missing_divisions) - 5} more')
        if missing_allocations:
            details.append(f'missing allocations: {", ".join(missing_allocations[:5])}')
            if len(missing_allocations) > 5:
                details.append(f'and {len(missing_allocations) - 5} more')
        flash('Data notice — ' + '; '.join(details) + '. Generated using available data.', 'warning')
    if shortages:
        details = [
            f'{item["course"]} Sem{item["semester"]} {item["division"]} '
            f'{item["subject"]}: {item["placed"]}/{item["required"]} hours'
            for item in shortages[:5]
        ]
        extra = f' and {len(shortages) - 5} more' if len(shortages) > 5 else ''
        flash('Scheduling notice — ' + '; '.join(details) + extra + '.', 'warning')
    flash(f'{session_type} Semester timetable generated — {len(entries)} entries.', 'success')
    return redirect(url_for('tt_bp.timetable_view', session_type=session_type))

@tt_bp.route('/timetable/lock/<int:eid>', methods=['POST'])
@login_required
def timetable_lock(eid):
    entry = db.session.get(Timetable, eid)
    if entry is None:
        return jsonify({'error': 'not found'}), 404
    entry.locked = not entry.locked
    db.session.commit()
    return jsonify({'locked': entry.locked})

@tt_bp.route('/timetable/export/excel', methods=['POST'])
@login_required
def export_excel():
    import io
    import openpyxl
    rows = _requested_timetable_export_rows()
    if rows is None:
        return jsonify({'error': 'Invalid timetable export data.'}), 400

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Timetable'
    ws.append(['Day', 'Slot', 'Faculty', 'Subject', 'Division', 'Room', 'Batch'])
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, download_name='timetable.xlsx',
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@tt_bp.route('/timetable/export/pdf', methods=['POST'])
@login_required
def export_pdf():
    import io
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib import colors
    rows = _requested_timetable_export_rows()
    if rows is None:
        return jsonify({'error': 'Invalid timetable export data.'}), 400

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
    data = [['Day', 'Slot', 'Faculty', 'Subject', 'Division', 'Room', 'Batch']]
    data.extend(rows)
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#222')),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
    ]))
    doc.build([t])
    buf.seek(0)
    return send_file(buf, download_name='timetable.pdf',
                     as_attachment=True, mimetype='application/pdf')
