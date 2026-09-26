from extensions import db
from models import Allocation, Division, Faculty, Room, Subject, Timetable


def init_db(app):
    with app.app_context():
        db.create_all()
        with db.engine.begin() as connection:
            for model in (Faculty, Subject, Division, Allocation, Timetable):
                for index in model.__table__.indexes:
                    index.create(bind=connection, checkfirst=True)
            connection.exec_driver_sql(
                'INSERT OR IGNORE INTO timetable_revision (id, revision, pending) VALUES (1, 0, 0)'
            )
            for table in ('timetable', 'faculty', 'subject', 'division', 'room', 'allocation'):
                for action in ('INSERT', 'UPDATE', 'DELETE'):
                    trigger = f'trg_{table}_revision_{action.lower()}'
                    connection.exec_driver_sql(f'''
                        CREATE TRIGGER IF NOT EXISTS {trigger}
                        AFTER {action} ON {table}
                        WHEN (SELECT pending FROM timetable_revision WHERE id = 1) = 0
                        BEGIN
                            UPDATE timetable_revision SET pending = 1 WHERE id = 1;
                        END
                    ''')
        with db.engine.connect() as connection:
            connection.exec_driver_sql('PRAGMA journal_mode=WAL')
        _seed_rooms()


def _seed_rooms():
    if Room.query.first() is not None:
        return
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
