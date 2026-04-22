from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from app.routes.auth import auth
    from app.routes.teacher import teacher
    from app.routes.student import student    # ← add this
    app.register_blueprint(auth)
    app.register_blueprint(teacher)
    app.register_blueprint(student)           # ← add this

    return app