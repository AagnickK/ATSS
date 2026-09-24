"""
Generate Faculty_Allocation_Full.xlsx
======================================
Division rules:
  All courses  -> divs A-I (9 divisions per semester)
  IMCA         -> div A only (1 division per semester)

Target: 24 hrs/week per division = 4 lectures/day x 6 days
  6 Theory (3h) + 2 Tutorial (2h) + 1 Lab (2h) = 24 hrs

Faculty: 85 total  VP=1 HOD=4 AP=5 Regular=75
Shift:   Morning -> MCA, MCA NEP, MSc IT, MSc IT NEP
         General -> everything else
"""
import random
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from collections import defaultdict

random.seed(42)

# Division rules per course (used only for importer expansion, not in Excel rows)
# Excel has one row per subject-course-sem; importer creates divisions
ALL_DIVS  = list('ABCDEFGHI')
IMCA_DIVS = ['A']

# (course, semesters, shift, students, divisions)
COURSES = [
    ('BSc IT',      list(range(1, 7)),  'General', 60, ALL_DIVS),
    ('BCA',         list(range(1, 7)),  'General', 60, ALL_DIVS),
    ('IMCA',        list(range(1, 11)), 'General', 60, IMCA_DIVS),
    ('MCA',         list(range(1, 5)),  'Morning', 40, ALL_DIVS),
    ('MCA NEP',     [3, 4],             'Morning', 40, ALL_DIVS),
    ('MSc IT',      list(range(1, 5)),  'Morning', 40, ALL_DIVS),
    ('MSc IT NEP',  [3, 4],             'Morning', 40, ALL_DIVS),
]

SUBJECT_BANK = {
    'BSc IT Hons': [
        'Discrete Mathematics','Data Structures','Computer Architecture','Software Engineering',
        'Operating Systems','Computer Networks','DBMS','Web Technologies','Python Programming',
        'Java Programming','Machine Learning','Cloud Computing','Cyber Security','Data Analytics',
        'Compiler Design','Computer Graphics','Mobile Computing','IoT Fundamentals',
        'Big Data Analytics','Blockchain Technology','Deep Learning','Natural Language Processing',
        'Distributed Systems','Information Security','Software Testing','Project Management',
        'Digital Image Processing','Wireless Networks','Embedded Systems','Research Methodology',
        'Advanced Algorithms','Microprocessors','Computer Vision','Quantum Computing',
        'Edge Computing','DevOps','Augmented Reality','Robotics','Data Mining','Ethics in IT',
    ],
    'BSc IT': [
        'Mathematics I','Programming in C','Digital Logic','Data Structures','DBMS','Web Development',
        'Operating Systems','Computer Networks','Python Programming','Software Engineering',
        'Machine Learning','Cyber Security','Java Programming','Cloud Computing','Data Analytics',
        'Mobile App Development','IoT','Blockchain','Big Data','Computer Graphics',
        'Compiler Design','Microprocessors','Information Security','Software Testing',
        'Project Management','Digital Electronics','Computer Architecture','Wireless Networks',
        'Embedded Systems','Research Methodology','Advanced Algorithms','Computer Vision',
        'Deep Learning','Natural Language Processing','Distributed Systems','DevOps',
        'Augmented Reality','Robotics','Data Mining','Ethics in IT',
    ],
    'BCA Hons': [
        'Mathematics I','Programming in C','Digital Electronics','Data Structures','DBMS',
        'Web Development','Operating Systems','Java Programming','Python Programming',
        'Computer Networks','Machine Learning','Cloud Computing','Cyber Security','Data Analytics',
        'Mobile App Development','IoT','Blockchain','Big Data','Computer Graphics',
        'Compiler Design','Microprocessors','Information Security','Software Testing',
        'Project Management','Software Engineering','Computer Architecture','Wireless Networks',
        'Embedded Systems','Research Methodology','Advanced Algorithms','Computer Vision',
        'Deep Learning','Natural Language Processing','Distributed Systems','DevOps',
        'Augmented Reality','Robotics','Data Mining','Ethics in IT','Discrete Mathematics',
    ],
    'BCA': [
        'Mathematics I','Programming in C','Digital Electronics','Data Structures','DBMS',
        'Web Development','Operating Systems','Java Programming','Python Programming',
        'Computer Networks','Machine Learning','Cyber Security','Software Engineering',
        'Cloud Computing','Data Analytics','Mobile App Development','IoT','Blockchain',
        'Big Data','Computer Graphics','Compiler Design','Microprocessors','Information Security',
        'Software Testing','Project Management','Computer Architecture','Wireless Networks',
        'Embedded Systems','Research Methodology','Advanced Algorithms','Computer Vision',
        'Deep Learning','Natural Language Processing','Distributed Systems','DevOps',
        'Augmented Reality','Robotics','Data Mining','Ethics in IT',
    ],
    'IMCA': [
        'Mathematics I','Programming in C','Digital Logic','Data Structures','DBMS','Web Development',
        'Operating Systems','Java Programming','Python Programming','Computer Networks',
        'Machine Learning','Cyber Security','Cloud Computing','Software Engineering',
        'Artificial Intelligence','Data Analytics','Cryptography','Network Security',
        'Big Data','Project Work','Advanced Algorithms','Computer Architecture',
        'Mobile Computing','IoT','Blockchain','Deep Learning','Natural Language Processing',
        'Distributed Systems','Information Security','Software Testing','Project Management',
        'Computer Vision','DevOps','Augmented Reality','Robotics','Data Mining',
        'Compiler Design','Microprocessors','Wireless Networks','Embedded Systems',
    ],
    'MCA': [
        'Advanced Algorithms','Software Engineering','Computer Architecture','DBMS',
        'Operating Systems','Computer Networks','Machine Learning','Cloud Computing',
        'Cyber Security','Data Analytics','Mobile Computing','IoT','Blockchain',
        'Deep Learning','Natural Language Processing','Distributed Systems',
        'Information Security','Software Testing','Project Management','Computer Vision',
        'DevOps','Augmented Reality','Robotics','Data Mining','Compiler Design',
        'Microprocessors','Wireless Networks','Embedded Systems','Research Methodology',
        'Advanced Mathematics','Data Science','Quantum Computing','Edge Computing',
        'Digital Image Processing','Formal Methods','Parallel Computing','Grid Computing',
        'Service Oriented Architecture','Enterprise Architecture','IT Governance',
    ],
    'MCA NEP': [
        'Advanced Algorithms','Research Methodology','Computer Architecture','DBMS',
        'Operating Systems','Computer Networks','Machine Learning','Cloud Computing',
        'Cyber Security','Data Analytics','Mobile Computing','IoT','Blockchain',
        'Deep Learning','Natural Language Processing','Distributed Systems',
        'Information Security','Software Testing','Project Management','Computer Vision',
        'DevOps','Augmented Reality','Robotics','Data Mining','Compiler Design',
        'Microprocessors','Wireless Networks','Embedded Systems','Advanced Mathematics',
        'Data Science','Quantum Computing','Edge Computing','Digital Image Processing',
        'Formal Methods','Parallel Computing','Grid Computing','Software Engineering',
        'Enterprise Architecture','IT Governance','Ethics in Computing',
    ],
    'MSc IT': [
        'Advanced Mathematics','Data Science','Computer Architecture','DBMS',
        'Operating Systems','Computer Networks','Machine Learning','Cloud Computing',
        'Cyber Security','Data Analytics','Mobile Computing','IoT','Blockchain',
        'Deep Learning','Natural Language Processing','Distributed Systems',
        'Information Security','Software Testing','Project Management','Computer Vision',
        'DevOps','Augmented Reality','Robotics','Data Mining','Compiler Design',
        'Microprocessors','Wireless Networks','Embedded Systems','Research Methodology',
        'Advanced Algorithms','Quantum Computing','Edge Computing','Digital Image Processing',
        'Formal Methods','Parallel Computing','Grid Computing','Software Engineering',
        'Enterprise Architecture','IT Governance','Ethics in Computing',
    ],
    'MSc IT NEP': [
        'Advanced Mathematics','Research Methodology','Computer Architecture','DBMS',
        'Operating Systems','Computer Networks','Machine Learning','Cloud Computing',
        'Cyber Security','Data Analytics','Mobile Computing','IoT','Blockchain',
        'Deep Learning','Natural Language Processing','Distributed Systems',
        'Information Security','Software Testing','Project Management','Computer Vision',
        'DevOps','Augmented Reality','Robotics','Data Mining','Compiler Design',
        'Microprocessors','Wireless Networks','Embedded Systems','Advanced Algorithms',
        'Data Science','Quantum Computing','Edge Computing','Digital Image Processing',
        'Formal Methods','Parallel Computing','Grid Computing','Software Engineering',
        'Enterprise Architecture','IT Governance','Ethics in Computing',
    ],
}


def subjects_for(course, sem):
    """
    6 Theory (3h) + 2 Tutorial (2h) + 1 Lab (2h) = 24 hrs/week per division.
    Exactly 4 lectures/day across 6 days.
    """
    bank  = SUBJECT_BANK[course]
    total = len(bank)
    idx   = ((sem - 1) * 9) % total
    result = []
    for i in range(6):
        result.append((bank[(idx + i) % total], 'Theory', 3, 0))
    result.append((bank[(idx + 6) % total] + ' Tutorial', 'Theory', 2, 0))
    result.append((bank[(idx + 7) % total] + ' Seminar',  'Theory', 2, 0))
    result.append((bank[(idx + 8) % total] + ' Lab',      'Lab',    0, 2))
    return result  # 6*3 + 2 + 2 + 2 = 24 hrs


DEPTS = ['Computer Science', 'Information Technology', 'Mathematics', 'Electronics']


def make_faculty():
    pool = []
    fid  = 1001

    pool.append({'faculty_id': f'FAC-{fid}', 'faculty_name': 'Dr. V. Principal',
                 'designation': 'Vice Principal', 'department': 'Computer Science',
                 'shift': 'General', 'max_hours': 6, 'email': f'fac{fid}@college.edu'})
    fid += 1

    for name in ['Dr. A. Kumar', 'Dr. B. Singh', 'Dr. C. Patel', 'Dr. D. Sharma']:
        pool.append({'faculty_id': f'FAC-{fid}', 'faculty_name': name,
                     'designation': 'HOD', 'department': random.choice(DEPTS),
                     'shift': 'General', 'max_hours': 12, 'email': f'fac{fid}@college.edu'})
        fid += 1

    for name in ['Dr. E. Mehta', 'Dr. F. Joshi', 'Dr. G. Rao', 'Dr. H. Nair', 'Dr. I. Verma']:
        pool.append({'faculty_id': f'FAC-{fid}', 'faculty_name': name,
                     'designation': 'Associate Professor', 'department': random.choice(DEPTS),
                     'shift': 'General', 'max_hours': 14, 'email': f'fac{fid}@college.edu'})
        fid += 1

    reg_first = [
        'Prof. Amit','Prof. Priya','Prof. Rahul','Prof. Sneha','Prof. Vijay',
        'Prof. Anita','Prof. Suresh','Prof. Kavita','Prof. Ravi','Prof. Meena',
        'Prof. Arun','Prof. Pooja','Prof. Nitin','Prof. Sunita','Prof. Deepak',
        'Prof. Rekha','Prof. Manoj','Prof. Geeta','Prof. Sanjay','Prof. Usha',
        'Prof. Kiran','Prof. Mohan','Prof. Lata','Prof. Ashok','Prof. Nisha',
        'Prof. Tarun','Prof. Smita','Prof. Vinod','Prof. Asha','Prof. Rajesh',
        'Prof. Seema','Prof. Hemant','Prof. Jyoti','Prof. Prakash','Prof. Manju',
        'Prof. Sunil','Prof. Poonam','Prof. Girish','Prof. Vandana','Prof. Naresh',
        'Prof. Alka','Prof. Dinesh','Prof. Shobha','Prof. Ramesh','Prof. Nita',
        'Prof. Yogesh','Prof. Sarla','Prof. Bharat','Prof. Kamla','Prof. Vivek',
        'Prof. Renu','Prof. Harish','Prof. Sudha','Prof. Ajay','Prof. Mala',
        'Prof. Pankaj','Prof. Vimla','Prof. Rakesh','Prof. Hema','Prof. Gaurav',
        'Prof. Shanta','Prof. Mukesh','Prof. Rani','Prof. Lalit','Prof. Savita',
        'Prof. Umesh','Prof. Pushpa','Prof. Naveen','Prof. Chanda','Prof. Satish',
        'Prof. Mamta','Prof. Anil','Prof. Sharda','Prof. Kapil','Prof. Neeta',
    ]
    last = ['Sharma','Verma','Gupta','Singh','Patel','Mehta','Joshi','Rao','Nair','Tiwari']
    for i, first in enumerate(reg_first):
        shift = 'Morning' if i < 38 else 'General'
        pool.append({'faculty_id': f'FAC-{fid}',
                     'faculty_name': f'{first} {last[i % len(last)]}',
                     'designation': 'Regular Faculty',
                     'department': random.choice(DEPTS),
                     'shift': shift, 'max_hours': 18,
                     'email': f'fac{fid}@college.edu'})
        fid += 1

    return pool


def build_rows(faculty_pool):
    """
    One row per (faculty, subject, course, sem).
    No division column — importer expands to all divisions for that course.
    Faculty teaches the same subject to all divisions of a course (shared allocation).
    """
    rows        = []
    hours_used  = defaultdict(int)
    morning_fac = [f for f in faculty_pool if f['shift'] == 'Morning']
    general_fac = [f for f in faculty_pool if f['shift'] == 'General']

    def pick(shift, hrs):
        pool  = morning_fac if shift == 'Morning' else general_fac
        cands = [f for f in pool if hours_used[f['faculty_id']] + hrs <= f['max_hours']]
        if not cands:
            cands = [f for f in faculty_pool if hours_used[f['faculty_id']] + hrs <= f['max_hours']]
        if not cands:
            return None
        weights = [f['max_hours'] - hours_used[f['faculty_id']] for f in cands]
        return random.choices(cands, weights=weights, k=1)[0]

    for course, semesters, shift, students, divisions in COURSES:
        for sem in semesters:
            for (sname, stype, lh, labh) in subjects_for(course, sem):
                hrs = lh if stype == 'Theory' else labh
                fac = pick(shift, hrs)
                if fac is None:
                    continue
                hours_used[fac['faculty_id']] += hrs
                rows.append({
                    'faculty_id':    fac['faculty_id'],
                    'faculty_name':  fac['faculty_name'],
                    'designation':   fac['designation'],
                    'department':    fac['department'],
                    'shift':         fac['shift'],
                    'max_hours':     fac['max_hours'],
                    'email':         fac['email'],
                    'subject_name':  sname,
                    'course':        course,
                    'semester':      sem,
                    'type':          stype,
                    'lecture_hours': lh,
                    'lab_hours':     labh,
                    'students':      students,
                })
    return rows


def write_excel(rows, path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Allocation'
    # No division column — importer expands per course
    headers = ['faculty_id','faculty_name','designation','department','shift','max_hours',
               'email','subject_name','course','semester','type','lecture_hours','lab_hours',
               'students']
    fill = PatternFill('solid', fgColor='FF9000')
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = Font(bold=True, color='18181B')
        c.fill = fill
        c.alignment = Alignment(horizontal='center')
        ws.column_dimensions[c.column_letter].width = max(len(h) + 4, 14)
    for row in rows:
        ws.append([row[h] for h in headers])
    wb.save(path)
    print(f'Saved {len(rows)} rows to {path}')


if __name__ == '__main__':
    faculty_pool = make_faculty()
    print(f'Faculty: {len(faculty_pool)} (VP=1 HOD=4 AP=5 Reg=75)')
    rows = build_rows(faculty_pool)
    print(f'Rows: {len(rows)}')
    used = defaultdict(int)
    for r in rows:
        used[r['faculty_id']] += r['lecture_hours'] or r['lab_hours']
    caps  = {f['faculty_id']: f['max_hours'] for f in faculty_pool}
    over  = [(fid, used[fid], caps[fid]) for fid in used if used[fid] > caps[fid]]
    print(f'Overloaded faculty: {len(over)}')
    div_hrs = defaultdict(int)
    for r in rows:
        div_hrs[(r['course'], r['semester'], r['division'])] += r['lecture_hours'] or r['lab_hours']
    vals = list(div_hrs.values())
    print(f'Hrs/div/week: min={min(vals)} max={max(vals)} avg={round(sum(vals)/len(vals),2)}')
    print(f'Total hrs needed: {sum(vals)}, Faculty cap: {sum(caps.values())}')
    write_excel(rows, 'data/Faculty_Allocation_Full.xlsx')
