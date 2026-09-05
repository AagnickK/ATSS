from flask import Flask
from pathlib import Path
from flask_wtf.csrf import generate_csrf
from config import Config
from extensions import db, login_manager, bcrypt, csrf
from database import init_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['ATSS_DOC_DIR'] = Path(app.root_path) / 'atss_doc'

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)

    app.jinja_env.globals['csrf_token'] = generate_csrf

    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from routes import auth, main, faculty_bp, subject_bp, room_bp, tt_bp
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(subject_bp)
    app.register_blueprint(room_bp)
    app.register_blueprint(tt_bp)

    init_db(app)
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        debug=True,
        extra_files=[],
        exclude_patterns=[
            '*\\site-packages\\*',
            '*\\Python310\\Lib\\*',
        ],
    )
