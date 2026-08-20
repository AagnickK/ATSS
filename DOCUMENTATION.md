# ATSS — Automatic Timetable Scheduling System
### Technical Documentation

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [File Structure & Responsibilities](#3-file-structure--responsibilities)
4. [Architecture](#4-architecture)
5. [Database Schema](#5-database-schema)
6. [Module Deep-Dive](#6-module-deep-dive)
7. [Algorithm — CP-SAT Scheduler](#7-algorithm--cp-sat-scheduler)
8. [Flowcharts](#8-flowcharts)
9. [API / Route Reference](#9-api--route-reference)
10. [Configuration Reference](#10-configuration-reference)
11. [Data Flow — Excel Import](#11-data-flow--excel-import)
12. [OTP Email Flow](#12-otp-email-flow)
13. [Room Seeding Logic](#13-room-seeding-logic)

---

## 1. Project Overview

ATSS (Automatic Timetable Scheduling System) is a Flask web application that:
- Manages faculty, subjects, divisions, and rooms
- Automatically generates conflict-free timetables using **Google OR-Tools CP-SAT solver**
- Supports OTP-based email verification for registration and password reset
- Exports timetables to Excel and PDF
- Enforces hard scheduling constraints (no double-booking of faculty, rooms, or divisions)

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Web Framework | Flask 3.x |
| ORM | Flask-SQLAlchemy (SQLite) |
| Auth | Flask-Login + Flask-Bcrypt |
| CSRF Protection | Flask-WTF |
| Scheduler | Google OR-Tools CP-SAT |
| Email / OTP | smtplib + Gmail SMTP |
| Excel Import | pandas + openpyxl |
| PDF Export | ReportLab |
| Frontend | Jinja2 templates + vanilla CSS/JS |

---

## 3. File Structure & Responsibilities

```
atss_python/
│
├── app.py              ← App factory, blueprint registration, DB init
├── config.py           ← Config class, time slots, days, enums
├── extensions.py       ← db, login_manager, bcrypt, csrf instances
├── models.py           ← All SQLAlchemy ORM models
├── routes.py           ← All blueprints and route handlers
├── database.py         ← DB init + room seeding
├── scheduler.py        ← CP-SAT timetable generation engine
├── constraints.py      ← Hard/soft constraint definitions
├── importer.py         ← Excel → DB faculty/subject/division importer
├── otp.py              ← OTP generation and Gmail SMTP sender
├── .env                ← Gmail credentials (not committed)
│
├── templates/
│   ├── base.html       ← Sidebar nav layout, flash messages
│   ├── dashboard.html  ← Stats overview
│   ├── faculty.html    ← Faculty list, add form, Excel import
│   ├── subjects.html   ← Subject list and add form
│   ├── classroom.html  ← Room list and add form
│   ├── timetable.html  ← Timetable grid, generate, export
│   ├── login.html      ← Login form
│   ├── register.html   ← Registration form
│   ├── verify_otp.html ← OTP input form (register + forgot password)
│   ├── forgot_password.html ← Email input for password reset
│   ├── reset_password.html  ← New password form
│   └── setup_gmail.html     ← Gmail credentials setup
│
├── static/
│   ├── css/app.css     ← Main application styles
│   ├── style.css       ← Auth page styles
│   ├── js/app.js       ← Frontend JS (lock toggle, etc.)
│   └── cursor.js       ← Custom cursor animation
│
├── instance/
│   └── timetable.db    ← SQLite database (auto-created)
│
└── data/               ← Uploaded Excel files (temporary)
```

### File Dependency Map

```
app.py
 ├── extensions.py   (db, login_manager, bcrypt, csrf)
 ├── models.py       (imports db from extensions)
 ├── routes.py       (imports db, bcrypt from extensions; models; config; otp)
 ├── database.py     (imports db, models)
 └── config.py       (standalone — no internal imports)

scheduler.py
 ├── config.py       (DAYS, SLOTS)
 └── constraints.py  (hard constraint functions)

importer.py
 ├── extensions.py   (db)
 └── models.py       (Faculty, Subject, Division, Allocation)

otp.py              (standalone — uses smtplib, dotenv)
```

---

## 4. Architecture

### App Factory Pattern

```
create_app()  [app.py]
    │
    ├── Flask(__name__)
    ├── app.config.from_object(Config)
    │
    ├── db.init_app(app)           ← SQLAlchemy
    ├── login_manager.init_app(app)← Flask-Login
    ├── bcrypt.init_app(app)       ← Password hashing
    ├── csrf.init_app(app)         ← CSRF protection
    │
    ├── Register Blueprints
    │   ├── auth          → /login, /register, /verify-otp, /logout
    │   ├── main          → /, /dashboard
    │   ├── faculty_bp    → /faculty, /faculty/add, /faculty/delete, /faculty/import
    │   ├── subject_bp    → /subjects, /subjects/add, /subjects/delete
    │   ├── room_bp       → /rooms, /rooms/add, /rooms/delete
    │   └── tt_bp         → /timetable, /timetable/generate, /export/excel, /export/pdf
    │
    └── init_db(app)               ← create_all() + seed rooms
```

### Blueprint Separation

Each feature domain is isolated in its own Blueprint inside `routes.py`:

| Blueprint | Prefix | Purpose |
|---|---|---|
| `auth` | — | Login, register, OTP, logout |
| `main` | — | Index redirect, dashboard |
| `faculty_bp` | — | Faculty CRUD + Excel import |
| `subject_bp` | — | Subject CRUD |
| `room_bp` | — | Room CRUD |
| `tt_bp` | — | Timetable view, generate, lock, export |

---

## 5. Database Schema

```
┌─────────┐       ┌───────────┐       ┌──────────┐
│  User   │       │  Faculty  │       │ Subject  │
├─────────┤       ├───────────┤       ├──────────┤
│ id (PK) │       │ id (PK)   │       │ id (PK)  │
│username │       │ name      │       │ name     │
│ email   │       │designation│       │ course   │
│password │       │department │       │ semester │
│  role   │       │  shift    │       │  type    │
└─────────┘       │ max_hours │       │lec_hours │
                  │  email    │       │lab_hours │
                  └─────┬─────┘       └────┬─────┘
                        │                  │
                        └────────┬─────────┘
                                 │
                          ┌──────▼──────┐
                          │ Allocation  │
                          ├─────────────┤
                          │  id (PK)    │
                          │ faculty_id  │──→ Faculty
                          │ subject_id  │──→ Subject
                          │ division_id │──→ Division
                          └──────┬──────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │              Timetable               │
              ├──────────────────────────────────────┤
              │ id (PK)                              │
              │ day        (Monday–Saturday)         │
              │ slot       (1–6)                     │
              │ faculty_id ──→ Faculty               │
              │ subject_id ──→ Subject               │
              │ division_id──→ Division              │
              │ room_id    ──→ Room                  │
              │ batch      (Batch1/Batch2/null)      │
              │ locked     (bool)                    │
              └──────────────────────────────────────┘

┌──────────┐       ┌──────────┐
│ Division │       │   Room   │
├──────────┤       ├──────────┤
│ id (PK)  │       │ id (PK)  │
│ course   │       │ room_no  │
│ semester │       │  type    │
│ division │       │ capacity │
│ students │       │ building │
│  shift   │       └──────────┘
└──────────┘
```

---

## 6. Module Deep-Dive

### `extensions.py`
Single source of truth for all Flask extension instances. Prevents circular imports by keeping instances separate from the app factory.

```python
db            = SQLAlchemy()    # ORM
login_manager = LoginManager()  # Session auth
bcrypt        = Bcrypt()        # Password hashing
csrf          = CSRFProtect()   # CSRF tokens on all POST forms
```

### `models.py`
Defines all ORM models. Imports `db` from `extensions.py` only — no Flask app dependency, avoiding circular imports.

Key relationships:
- `Faculty` → `Allocation` (one-to-many)
- `Subject` → `Allocation` (one-to-many)
- `Division` → `Allocation` (one-to-many)
- `Allocation` → `Timetable` (via foreign keys)
- `Room` → `Timetable` (one-to-many)

### `config.py`
Stateless configuration. Defines:
- `MORNING_SLOTS` — 7:30 AM to 2:10 PM (6 slots)
- `GENERAL_SLOTS` — 9:30 AM to 4:20 PM (6 slots)
- `DAYS` — Monday to Saturday
- Enum lists for designations, shifts, subject types, room types

### `database.py`
Called once at startup via `init_db(app)`:
1. Runs `db.create_all()` — creates all tables if not present
2. Runs `_seed_rooms()` — always wipes and reseeds the 50 rooms

### `otp.py`
Standalone module. Loads Gmail credentials from `.env` at import time. Exposes:
- `configure(email, password)` — updates credentials in memory and `.env`
- `is_configured()` — checks if credentials are set
- `generate_otp()` — returns a random 6-digit string
- `send_otp(to_email, otp)` — sends via Gmail SMTP with STARTTLS

---

## 7. Algorithm — CP-SAT Scheduler

The timetable generator in `scheduler.py` uses **Constraint Programming with SAT** via Google OR-Tools.

### Inputs
| Input | Source |
|---|---|
| `allocations` | All `Allocation` rows (faculty → subject → division) |
| `faculty_map` | `{id: Faculty}` |
| `subject_map` | `{id: Subject}` |
| `division_map`| `{id: Division}` |
| `room_list` | All `Room` rows |

### Step-by-Step Algorithm

```
Step 1 — Build Decision Variables
──────────────────────────────────
For every combination of:
  (faculty_id, subject_id, division_id, day, slot_no)
Create a BoolVar:
  slot_vars[key] = model.new_bool_var(...)

  → 1 means "this subject is taught at this day/slot"
  → 0 means it is not

Step 2 — Weekly Hours Constraint
──────────────────────────────────
For each allocation:
  sum of all slot_vars for that (faculty, subject, division)
  across all days and slots == subject.lecture_hours (Theory)
                            OR subject.lab_hours (Lab)

  This forces exactly the right number of sessions per week.

Step 3 — Hard Constraints (constraints.py)
───────────────────────────────────────────
  HC1: Faculty clash prevention
       For each (faculty, day, slot):
         sum of all slot_vars <= 1
       → Faculty cannot teach two classes simultaneously

  HC2: Division clash prevention
       For each (division, day, slot):
         sum of all slot_vars <= 1
       → A division cannot have two subjects at the same time

  HC3: Weekly hours cap
       For each faculty:
         sum of all their slot_vars <= faculty.max_hours
       → Respects contractual teaching limits

Step 4 — Solve
───────────────
  solver.parameters.max_time_in_seconds = 60
  status = solver.solve(model)
  Accepts OPTIMAL or FEASIBLE solutions.

Step 5 — Room Assignment (post-solve greedy)
─────────────────────────────────────────────
  For each slot_var where solver.value == 1:

  If subject.type == 'Lab':
    batches = ceil(division.students / 30)
    Assign `batches` free lab rooms for that (day, slot)
    Create one Timetable entry per batch

  If subject.type == 'Theory':
    Find first classroom where:
      capacity >= division.students
      AND room not already used at (day, slot)
    Create one Timetable entry

Step 6 — Return
────────────────
  Return list of dicts → bulk inserted into Timetable table
```

### Complexity
- Variables: `|allocations| × |DAYS| × |SLOTS|` = up to ~thousands of BoolVars
- Solver timeout: 60 seconds (returns best feasible solution found)
- Room assignment: O(n) greedy after solve

---

## 8. Flowcharts

### 8.1 Application Startup

```
python app.py
     │
     ▼
create_app()
     │
     ├── Init extensions (db, login_manager, bcrypt, csrf)
     ├── Register 6 blueprints
     │
     ▼
init_db(app)
     │
     ├── db.create_all()  ← creates tables if missing
     │
     └── _seed_rooms()
           │
           ├── DELETE all rooms
           ├── INSERT 3   classrooms (301-303)
           ├── INSERT 11  classrooms (501-511)
           ├── INSERT 11  classrooms (C601-C611)
           ├── INSERT 13  labs       (L601-L613)
           └── INSERT 12  labs       (L702-L713)
                          Total: 25 classrooms + 25 labs
     │
     ▼
app.run(debug=True)
```

### 8.2 User Registration Flow

```
GET /register
     │
     ▼
Fill form (username, email, password)
     │
     ▼
POST /register
     │
     ├── Username already exists? ──YES──→ flash error → back to /register
     │
     ├── Gmail configured? ──NO──→ flash error → back to /register
     │
     ├── Generate 6-digit OTP
     ├── Store in session: {pending_user, otp_code, otp_email}
     ├── Send OTP email via Gmail SMTP
     │
     ▼
Redirect → GET /verify-otp
     │
     ▼
User enters OTP
     │
POST /verify-otp
     │
     ├── OTP matches session? ──NO──→ flash "Incorrect OTP" → stay
     │
     └── YES
           │
           ├── Create User in DB (bcrypt hashed password)
           ├── Clear session
           ├── flash "Account created"
           └── Redirect → /login
```

### 8.3 Forgot Password Flow

```
GET /forgot-password
     │
     ▼
Enter email
     │
POST /forgot-password
     │
     ├── Gmail configured? ──NO──→ flash error
     │
     ├── Email in DB? ──NO──→ flash generic message (no info leak)
     │
     └── YES
           ├── Generate OTP
           ├── Store session: {otp, otp_email}
           ├── Send OTP email
           └── Redirect → /verify-otp
                    │
                    ▼
              OTP correct?
                    │
              ──YES─┘
                    │
                    ├── session[otp_verified] = True
                    └── Redirect → /reset-password
                                       │
                                       ▼
                               Enter new password
                                       │
                               Passwords match?
                                       │
                               ──YES───┘
                                       │
                               Update User.password (bcrypt)
                               Clear session
                               Redirect → /login
```

### 8.4 Timetable Generation Flow

```
Click "Generate Timetable"
     │
POST /timetable/generate
     │
     ├── DELETE all unlocked Timetable entries
     │
     ├── Load from DB:
     │   ├── allocations  (faculty → subject → division)
     │   ├── faculty_map
     │   ├── subject_map
     │   ├── division_map
     │   └── room_list
     │
     ▼
generate_timetable() [scheduler.py]
     │
     ├── Build CP-SAT BoolVars for every possible slot
     ├── Add weekly hours == required constraint
     ├── Add hard constraints (faculty clash, division clash, hours cap)
     │
     ├── solver.solve() ← max 60 seconds
     │
     ├── INFEASIBLE? ──→ return [] → flash warning
     │
     └── FEASIBLE/OPTIMAL
           │
           ├── For each active slot:
           │   ├── Lab → assign batches to free lab rooms
           │   └── Theory → assign first suitable classroom
           │
           └── Return list of Timetable dicts
     │
     ▼
Bulk insert into Timetable table
     │
     ▼
Redirect → /timetable  (view results)
```

### 8.5 Excel Import Flow

```
Choose .xlsx file → POST /faculty/import
     │
     ▼
importer.import_faculty_excel(filepath)
     │
     ├── pandas.read_excel()
     ├── Normalize column names (lowercase, underscores)
     │
     └── For each row:
           │
           ├── Extract faculty_name
           │   └── Skip if empty/nan
           │
           ├── Faculty exists? ──NO──→ INSERT Faculty → flush
           │
           ├── Extract subject_name
           │   └── Skip if empty/nan
           │
           ├── Subject exists (name+course+semester)? ──NO──→ INSERT Subject → flush
           │
           ├── Division exists (course+semester+division)? ──NO──→ INSERT Division → flush
           │
           └── Allocation exists? ──NO──→ INSERT Allocation
     │
     ▼
db.session.commit()
     │
     ▼
flash "Imported N faculty records"
Redirect → /faculty
```

---

## 9. API / Route Reference

### Auth Blueprint
| Method | Route | Description |
|---|---|---|
| GET/POST | `/login` | Login with username + password |
| GET/POST | `/register` | Register → triggers OTP email |
| GET/POST | `/verify-otp` | Verify OTP (register or forgot-password) |
| GET | `/logout` | Logout current user |

### Main Blueprint
| Method | Route | Description |
|---|---|---|
| GET | `/` | Redirect to login |
| GET | `/dashboard` | Stats overview (auth required) |

### Faculty Blueprint
| Method | Route | Description |
|---|---|---|
| GET | `/faculty` | List all faculty |
| POST | `/faculty/add` | Add single faculty |
| POST | `/faculty/delete/<id>` | Delete faculty by ID |
| POST | `/faculty/import` | Import from Excel file |

### Subject Blueprint
| Method | Route | Description |
|---|---|---|
| GET | `/subjects` | List all subjects |
| POST | `/subjects/add` | Add subject |
| POST | `/subjects/delete/<id>` | Delete subject |

### Room Blueprint
| Method | Route | Description |
|---|---|---|
| GET | `/rooms` | List all rooms |
| POST | `/rooms/add` | Add room |
| POST | `/rooms/delete/<id>` | Delete room |

### Timetable Blueprint
| Method | Route | Description |
|---|---|---|
| GET | `/timetable` | View timetable (filter by division/faculty) |
| POST | `/timetable/generate` | Run CP-SAT scheduler |
| POST | `/timetable/lock/<id>` | Toggle lock on entry |
| GET | `/timetable/export/excel` | Download as .xlsx |
| GET | `/timetable/export/pdf` | Download as .pdf |

---

## 10. Configuration Reference

### Time Slots

**Morning Shift**
| Slot | Start | End |
|---|---|---|
| 1 | 7:30 | 8:25 |
| 2 | 8:25 | 9:20 |
| 3 | 9:30 | 10:25 |
| 4 | 10:25 | 11:20 |
| 5 | 12:20 | 1:15 |
| 6 | 1:15 | 2:10 |

**General Shift**
| Slot | Start | End |
|---|---|---|
| 1 | 9:30 | 10:25 |
| 2 | 10:25 | 11:20 |
| 3 | 12:20 | 1:15 |
| 4 | 1:15 | 2:10 |
| 5 | 2:30 | 3:25 |
| 6 | 3:25 | 4:20 |

### Room Inventory (Auto-seeded)

| Type | Room Numbers | Count | Capacity |
|---|---|---|---|
| Classroom | 301, 302, 303 | 3 | 120 |
| Classroom | 501–511 | 11 | 80 |
| Classroom | C601–C611 | 11 | 80 |
| **Total Classrooms** | | **25** | |
| Lab | L601–L613 | 13 | 35 |
| Lab | L702–L713 | 12 | 35 |
| **Total Labs** | | **25** | |

### Environment Variables (`.env`)
```
SECRET_KEY=your-secret-key
GMAIL=your@gmail.com
GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
```

---

## 11. Data Flow — Excel Import

### Required Excel Columns
| Column | Alternate Name | Required |
|---|---|---|
| `faculty_name` | `name` | Yes |
| `designation` | — | No |
| `department` | — | No |
| `shift` | — | No (default: General) |
| `max_hours` | `weekly_hours` | No (default: 18) |
| `email` | — | No |
| `subject_name` | `subject` | No |
| `course` | — | No |
| `semester` | — | No |
| `type` | — | No (default: Theory) |
| `lecture_hours` | — | No (default: 3) |
| `lab_hours` | — | No (default: 0) |
| `division` | — | No (default: A) |
| `students` | — | No (default: 60) |

### Duplicate Handling
- Faculty matched by `name` — not re-inserted if exists
- Subject matched by `name + course + semester`
- Division matched by `course + semester + division`
- Allocation matched by `faculty_id + subject_id + division_id`

---

## 12. OTP Email Flow

```
otp.py loads on import
    │
    ├── load_dotenv(.env)
    ├── _from_mail    = os.getenv('GMAIL')
    └── _app_password = os.getenv('GMAIL_APP_PASSWORD')

send_otp(to_email, otp)
    │
    ├── Build EmailMessage
    ├── smtplib.SMTP('smtp.gmail.com', 587)
    ├── server.starttls()          ← encrypted connection
    ├── server.login(gmail, app_password)
    ├── server.send_message(msg)
    └── server.quit()              ← context manager auto-closes
```

> Gmail requires an **App Password** (not your account password).
> Generate at: https://myaccount.google.com/apppasswords

---

## 13. Room Seeding Logic

Rooms are wiped and reseeded every time the app starts via `_seed_rooms()` in `database.py`. This ensures the room inventory always matches the institutional spec regardless of manual DB changes.

```python
# Classrooms
301, 302, 303          → capacity 120  (ground floor large halls)
501 → 511              → capacity 80   (5th floor)
C601 → C611            → capacity 80   (6th floor classrooms)

# Labs (prefixed with L to avoid collision with C6xx classrooms)
L601 → L613            → capacity 35   (6th floor labs)
L702 → L713            → capacity 35   (7th floor labs)
```

The `C` and `L` prefixes on 6xx rooms distinguish classrooms from labs on the same floor since both occupy the 600-series numbering.
