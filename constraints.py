"""
Hard and soft constraint definitions used by the scheduler.
Each function receives the CP-SAT model variables and adds constraints.
"""
import math


def add_hard_constraints(model, slots, faculty_list, divisions, rooms):
    """
    slots: dict keyed by (faculty_id, subject_id, division_id, day, slot_no) -> BoolVar
    """
    # ── 1. Faculty cannot teach two divisions at the same time ───────────────
    from itertools import groupby
    from collections import defaultdict

    by_faculty_time = defaultdict(list)
    for key, var in slots.items():
        fid, sid, did, day, slot = key
        by_faculty_time[(fid, day, slot)].append(var)

    for vars_ in by_faculty_time.values():
        if len(vars_) > 1:
            model.add(sum(vars_) <= 1)

    # ── 2. Room cannot host two classes at the same time ────────────────────
    # (handled in scheduler.py via room assignment variables)

    # ── 3. Division cannot have two subjects at the same time ───────────────
    by_division_time = defaultdict(list)
    for key, var in slots.items():
        fid, sid, did, day, slot = key
        by_division_time[(did, day, slot)].append(var)

    for vars_ in by_division_time.values():
        if len(vars_) > 1:
            model.add(sum(vars_) <= 1)


def weekly_hours_limit(model, slots, faculty_max_hours):
    """Faculty cannot exceed their weekly teaching hour limit."""
    from collections import defaultdict
    by_faculty = defaultdict(list)
    for key, var in slots.items():
        fid = key[0]
        by_faculty[fid].append(var)

    for fid, vars_ in by_faculty.items():
        limit = faculty_max_hours.get(fid, 18)
        model.add(sum(vars_) <= limit)


def lab_batch_count(students, capacity=30):
    """Return number of batches needed for a lab division."""
    return math.ceil(students / capacity)
