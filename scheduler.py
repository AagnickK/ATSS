"""
ATSS Scheduling Engine — Greedy slot-filler with clash detection.

Rules enforced:
    1. Six slots per division-day, with four preferred working slots.
    2. Working slots prioritize three theory entries and one lab entry.
    3. One self-study slot is added when a slot is available; remaining slots
         are free lectures, capped at two.
"""
import random
from collections import defaultdict
from config import (
    DAYS, MORNING_SLOTS, GENERAL_SLOTS,
    MIN_DAILY_LECTURES, PREFERRED_DAILY_LECTURES,
    MIN_DAILY_FREE_LECTURES, MAX_DAILY_FREE_LECTURES, MIN_SESSION_LECTURES,
    DAILY_WORKING_SLOTS, DAILY_THEORY_SLOTS, DAILY_LAB_SLOTS,
)
from constraints import lab_batch_count

WORK_DAYS = [d for d in DAYS if d != 'Saturday']


def _slots_for_shift(shift):
    return MORNING_SLOTS if shift == 'Morning' else GENERAL_SLOTS


def generate_timetable(allocations, faculty_map, subject_map, division_map, room_list,
                       return_diagnostics=False):
    classrooms = [r for r in room_list if r.type == 'Classroom']
    labs       = [r for r in room_list if r.type == 'Lab']

    faculty_busy      = defaultdict(set)   # fid        -> {(day, slot_no)}
    division_busy     = defaultdict(set)   # did        -> {(day, slot_no)}
    room_busy         = set()              # {(day, slot_no, room_id)}
    subject_day_count = defaultdict(int)   # (sid, did, day) -> count
    division_day_count = defaultdict(int)  # (did, day) -> scheduled slots placed
    theory_day_count = defaultdict(int)     # (did, day) -> theory slots placed
    lab_day_count = defaultdict(int)        # (did, day) -> lab slots placed

    result = []
    shortages = []

    # ── 1. Schedule allocations fairly ───────────────────────────────────────
    # Work in rounds so one division cannot consume all shared faculty/rooms
    # before the other divisions receive any periods.
    grouped_allocations = defaultdict(list)
    required_hours = {}
    placed_hours = defaultdict(int)
    for alloc in allocations:
        if alloc.faculty_id not in faculty_map or alloc.subject_id not in subject_map \
                or alloc.division_id not in division_map:
            continue
        subject = subject_map[alloc.subject_id]
        hours_needed = subject.lecture_hours if subject.type == 'Theory' else subject.lab_hours
        if hours_needed <= 0:
            continue
        key = (alloc.division_id, alloc.subject_id, alloc.faculty_id)
        grouped_allocations[alloc.division_id].append(alloc)
        required_hours[key] = hours_needed

    alloc_list = []
    division_order = sorted(grouped_allocations)
    for round_no in range(max(
        (required for required in required_hours.values()),
        default=0,
    )):
        # Shuffle priority each round so divisions do not permanently lose
        # shared faculty and room slots because of database ID ordering.
        fair_order = list(division_order)
        random.shuffle(fair_order)
        for did in fair_order:
            division_allocations = sorted(
                grouped_allocations[did],
                key=lambda alloc: (alloc.subject_id, alloc.faculty_id),
            )
            for alloc in division_allocations:
                key = (alloc.division_id, alloc.subject_id, alloc.faculty_id)
                if round_no < required_hours[key]:
                    alloc_list.append(alloc)

    for alloc in alloc_list:
        fid = alloc.faculty_id
        sid = alloc.subject_id
        did = alloc.division_id

        if fid not in faculty_map or sid not in subject_map or did not in division_map:
            continue

        faculty  = faculty_map[fid]
        subject  = subject_map[sid]
        division = division_map[did]

        hours_needed = 1

        shift      = faculty.shift or division.shift or 'General'
        time_slots = _slots_for_shift(shift)
        all_slot_nos = [s for s, _, _ in time_slots]

        # Prefer days below the daily target, then days with fewer slots.
        day_pool = sorted(
            DAYS,
            key=lambda d: (
                division_day_count[(did, d)] >= PREFERRED_DAILY_LECTURES,
                division_day_count[(did, d)],
                random.random(),
            )
        )
        candidates = [
            (day, slot_no)
            for day in day_pool
            for slot_no in all_slot_nos
        ]

        placed = 0
        for day, slot_no in candidates:
            if placed >= hours_needed:
                break

            # Max 2 of same subject per division per day
            if subject_day_count[(sid, did, day)] >= 2:
                continue
            # Faculty clash
            if (day, slot_no) in faculty_busy[fid]:
                continue
            # Division clash
            if (day, slot_no) in division_busy[did]:
                continue
            if division_day_count[(did, day)] >= DAILY_WORKING_SLOTS:
                continue
            if subject.type == 'Theory' and theory_day_count[(did, day)] >= DAILY_THEORY_SLOTS:
                continue
            if subject.type == 'Lab' and lab_day_count[(did, day)] >= DAILY_LAB_SLOTS:
                continue

            if subject.type == 'Lab':
                batches   = lab_batch_count(division.students)
                free_labs = [r for r in labs if (day, slot_no, r.id) not in room_busy][:batches]
                if len(free_labs) < batches:
                    continue
                for i, room in enumerate(free_labs):
                    room_busy.add((day, slot_no, room.id))
                    result.append({
                        'day': day, 'slot': slot_no,
                        'faculty_id': fid, 'subject_id': sid,
                        'division_id': did, 'room_id': room.id,
                        'batch': f'Batch{i+1}',
                    })
            else:
                free_rooms = [r for r in classrooms
                              if r.capacity >= division.students
                              and (day, slot_no, r.id) not in room_busy]
                if not free_rooms:
                    continue
                room = free_rooms[0]
                room_busy.add((day, slot_no, room.id))
                result.append({
                    'day': day, 'slot': slot_no,
                    'faculty_id': fid, 'subject_id': sid,
                    'division_id': did, 'room_id': room.id,
                    'batch': None,
                })

            faculty_busy[fid].add((day, slot_no))
            division_busy[did].add((day, slot_no))
            subject_day_count[(sid, did, day)] += 1
            division_day_count[(did, day)] += 1
            if subject.type == 'Theory':
                theory_day_count[(did, day)] += 1
            else:
                lab_day_count[(did, day)] += 1
            placed += 1

        if placed:
            placed_hours[(did, sid, fid)] += placed

    for (did, sid, fid), required in required_hours.items():
        placed = placed_hours[(did, sid, fid)]
        if placed < required:
            division = division_map[did]
            subject = subject_map[sid]
            shortages.append({
                'course': division.course,
                'semester': division.semester,
                'division': division.division,
                'subject': subject.subject_name,
                'placed': placed,
                'required': required,
            })

    # ── 2. Fill the four daily working slots for every division ──────────────
    # Prefer three theory slots and one lab slot. If the supplied allocations
    # do not contain that mix, use any available subject as the fallback.
    for did, division in division_map.items():
        division_allocations = grouped_allocations.get(did, [])
        has_lab_allocation = any(
            subject_map[alloc.subject_id].type == 'Lab'
            for alloc in division_allocations
        )
        has_theory_allocation = any(
            subject_map[alloc.subject_id].type == 'Theory'
            for alloc in division_allocations
        )
        for day in DAYS:
            working_slots = {
                (entry['day'], entry['slot'])
                for entry in result
                if entry['division_id'] == did and entry['subject_id'] is not None
            }
            candidates = sorted(
                division_allocations,
                key=lambda alloc: subject_map[alloc.subject_id].type != 'Theory',
            )
            # A sparse import may contain fewer than four subjects. Reuse the
            # available allocation only as a fallback to fill the daily target.
            candidates = candidates * DAILY_WORKING_SLOTS
            for alloc in candidates:
                if sum(slot_day == day for slot_day, _ in working_slots) >= DAILY_WORKING_SLOTS:
                    break
                subject = subject_map[alloc.subject_id]
                if subject.type == 'Theory' and theory_day_count[(did, day)] >= DAILY_THEORY_SLOTS \
                    and has_lab_allocation:
                    continue
                if subject.type == 'Lab' and has_theory_allocation \
                    and lab_day_count[(did, day)] >= DAILY_LAB_SLOTS:
                    continue
                slot_numbers = [slot for slot, _, _ in _slots_for_shift(
                    faculty_map[alloc.faculty_id].shift or division.shift or 'General'
                )]
                slot_no = next(
                    (slot for slot in slot_numbers if (day, slot) not in working_slots),
                    None,
                )
                if slot_no is None:
                    continue
                room_pool = labs if subject.type == 'Lab' else classrooms
                room = next(
                    (room for room in room_pool
                     if room.capacity >= division.students
                     and (day, slot_no, room.id) not in room_busy),
                    None,
                )
                if room:
                    room_busy.add((day, slot_no, room.id))
                result.append({
                    'day': day, 'slot': slot_no,
                    'faculty_id': alloc.faculty_id,
                    'subject_id': alloc.subject_id,
                    'division_id': did,
                    'room_id': room.id if room else None,
                    'batch': 'Batch1' if subject.type == 'Lab' else None,
                })
                faculty_busy[alloc.faculty_id].add((day, slot_no))
                division_busy[did].add((day, slot_no))
                working_slots.add((day, slot_no))
                division_day_count[(did, day)] += 1
                if subject.type == 'Theory':
                    theory_day_count[(did, day)] += 1
                else:
                    lab_day_count[(did, day)] += 1
                placed_hours[(did, alloc.subject_id, alloc.faculty_id)] += 1

    # ── 3. Self study: one slot after the four working slots ─────────────────
    for did, division in division_map.items():
        shift = division.shift or 'General'
        all_slot_nos = [slot for slot, _, _ in _slots_for_shift(shift)]
        for day in WORK_DAYS:
            slot_no = next(
                (slot for slot in all_slot_nos if (day, slot) not in division_busy[did]),
                None,
            )
            if slot_no is None:
                continue
            division_busy[did].add((day, slot_no))
            result.append({
                'day': day, 'slot': slot_no,
                'faculty_id': None, 'subject_id': None,
                'division_id': did, 'room_id': None,
                'batch': 'Self Study',
            })

    # ── 4. Free Lectures: one or two per day, Mon-Fri ─────────────────────────
    for did, division in division_map.items():
        shift        = division.shift or 'General'
        time_slots   = _slots_for_shift(shift)
        all_slot_nos = [s for s, _, _ in time_slots]

        for day in WORK_DAYS:
            busy = {s for (d, s) in division_busy[did] if d == day}
            # Only use end-of-day slots (>= 4) that are free
            end_free = sorted(
                [s for s in all_slot_nos if s >= 4 and s not in busy],
                reverse=True
            )
            if not end_free:
                end_free = sorted(s for s in all_slot_nos if s not in busy)
            if not end_free:
                continue
            chosen = end_free[:MAX_DAILY_FREE_LECTURES]
            if len(chosen) < MIN_DAILY_FREE_LECTURES:
                continue
            for slot_no in sorted(chosen):
                result.append({
                    'day': day, 'slot': slot_no,
                    'faculty_id': None, 'subject_id': None,
                    'division_id': did, 'room_id': None,
                    'batch': 'Free Lecture',
                })

    # Report division-days below the minimum teaching-lecture requirement.
    for did, division in division_map.items():
        for day in WORK_DAYS:
            lecture_count = division_day_count[(did, day)]
            if lecture_count < MIN_DAILY_LECTURES:
                shortages.append({
                    'course': division.course,
                    'semester': division.semester,
                    'division': division.division,
                    'subject': f'{day} daily lectures',
                    'placed': lecture_count,
                    'required': MIN_DAILY_LECTURES,
                })

    return (result, shortages) if return_diagnostics else result
