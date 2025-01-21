# your_project/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config


db = SQLAlchemy()
app = Flask(__name__)


def create_app():


    # Configure SQLite database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = True

    app.config.from_object(Config)

    db.init_app(app)


    # Create the database and tables if they don't exist
    with app.app_context():
        from .routes import main
        app.register_blueprint(main)

        db.create_all()  # This creates all tables defined by models

    return app
