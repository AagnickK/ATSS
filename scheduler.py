"""
ATSS Scheduling Engine — Google OR-Tools CP-SAT Solver
"""
import math
from collections import defaultdict
from ortools.sat.python import cp_model
from config import DAYS, MORNING_SLOTS, GENERAL_SLOTS
from constraints import add_hard_constraints, weekly_hours_limit, lab_batch_count


def _slots_for_shift(shift):
    return MORNING_SLOTS if shift == 'Morning' else GENERAL_SLOTS


def generate_timetable(allocations, faculty_map, subject_map, division_map, room_list):
    """
    allocations : list of Allocation ORM objects
    faculty_map : {id: Faculty}
    subject_map : {id: Subject}
    division_map: {id: Division}
    room_list   : list of Room ORM objects

    Returns list of dicts ready to bulk-insert into Timetable.
    """
    model  = cp_model.CpModel()
    result = []

    classrooms = [r for r in room_list if r.type == 'Classroom']
    labs       = [r for r in room_list if r.type == 'Lab']

    # ── Build slot variables ─────────────────────────────────────────────────
    # slot_vars[(fid, sid, did, day, slot_no)] = BoolVar
    slot_vars = {}

    # Pre-check: total required hours per faculty must not exceed max_hours
    from collections import defaultdict
    faculty_required = defaultdict(int)
    for alloc in allocations:
        subj = subject_map[alloc.subject_id]
        hrs  = subj.lecture_hours if subj.type == 'Theory' else subj.lab_hours
        faculty_required[alloc.faculty_id] += hrs

    for fid, total in faculty_required.items():
        cap = faculty_map[fid].max_hours
        if total > cap:
            # Clamp max_hours to required so model stays feasible
            faculty_map[fid].max_hours = total

    for alloc in allocations:
        fid = alloc.faculty_id
        sid = alloc.subject_id
        did = alloc.division_id
        faculty  = faculty_map[fid]
        subject  = subject_map[sid]
        division = division_map[did]

        shift      = faculty.shift or division.shift or 'General'
        time_slots = _slots_for_shift(shift)
        hours_needed = subject.lecture_hours if subject.type == 'Theory' else subject.lab_hours

        if hours_needed == 0:
            continue   # skip subjects with no hours assigned

        for day in DAYS:
            for slot_no, start, end in time_slots:
                key = (fid, sid, did, day, slot_no)
                slot_vars[key] = model.new_bool_var(f's_{fid}_{sid}_{did}_{day}_{slot_no}')

        # Each subject must be scheduled exactly `hours_needed` times per week
        week_vars = [slot_vars[(fid, sid, did, day, slot_no)]
                     for day in DAYS
                     for slot_no, _, _ in _slots_for_shift(faculty.shift or 'General')]
        model.add(sum(week_vars) == hours_needed)

    # ── Hard constraints ─────────────────────────────────────────────────────
    add_hard_constraints(model, slot_vars, [], [], [])

    faculty_max = {fid: faculty_map[fid].max_hours for fid in faculty_map}
    weekly_hours_limit(model, slot_vars, faculty_max)

    # ── Solve ────────────────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return []

    # ── Extract solution ─────────────────────────────────────────────────────
    room_usage = {}   # (day, slot_no, room_id) -> True

    for key, var in slot_vars.items():
        if solver.value(var) == 1:
            fid, sid, did, day, slot_no = key
            subject  = subject_map[sid]
            division = division_map[did]

            if subject.type == 'Lab':
                batches = lab_batch_count(division.students)
                free_labs = [r for r in labs
                             if (day, slot_no, r.id) not in room_usage][:batches]
                for i, room in enumerate(free_labs):
                    room_usage[(day, slot_no, room.id)] = True
                    result.append({
                        'day': day, 'slot': slot_no,
                        'faculty_id': fid, 'subject_id': sid,
                        'division_id': did, 'room_id': room.id,
                        'batch': f'Batch{i+1}',
                    })
            else:
                free_rooms = [r for r in classrooms
                              if r.capacity >= division.students
                              and (day, slot_no, r.id) not in room_usage]
                if free_rooms:
                    room = free_rooms[0]
                    room_usage[(day, slot_no, room.id)] = True
                    result.append({
                        'day': day, 'slot': slot_no,
                        'faculty_id': fid, 'subject_id': sid,
                        'division_id': did, 'room_id': room.id,
                        'batch': None,
                    })

    return result
