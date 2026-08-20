from flask import Flask
from flask_wtf.csrf import generate_csrf
from config import Config
from extensions import db, login_manager, bcrypt, csrf
from database import init_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)

    app.jinja_env.globals['csrf_token'] = generate_csrf

    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

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
    app.run(debug=True)
