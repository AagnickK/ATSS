from extensions import db
from models import Room
from config import DAYS, MORNING_SLOTS, GENERAL_SLOTS


def init_db(app):
    with app.app_context():
        db.create_all()
        _seed_rooms()


def _seed_rooms():
    Room.query.delete()
    db.session.commit()
    rooms = []
    for n in [301, 302, 303]:
        rooms.append(Room(room_no=str(n),   type='Classroom', capacity=120, building='Main'))
    for n in range(501, 512):
        rooms.append(Room(room_no=str(n),   type='Classroom', capacity=80,  building='Main'))
    for n in range(601, 612):
        rooms.append(Room(room_no=f'C{n}',  type='Classroom', capacity=80,  building='Main'))
    for n in range(601, 614):
        rooms.append(Room(room_no=f'L{n}',  type='Lab',       capacity=35,  building='Main'))
    for n in range(702, 714):
        rooms.append(Room(room_no=f'L{n}',  type='Lab',       capacity=35,  building='Main'))
    db.session.bulk_save_objects(rooms)
    db.session.commit()
