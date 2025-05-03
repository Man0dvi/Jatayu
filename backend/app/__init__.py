from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

db = SQLAlchemy()

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

    db.init_app(app)

    # Import models
    from app.models.user import User
    from app.models.job import JobDescription, RequiredSkill
    from app.models.skill import Skill

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.recruiter import recruiter_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(recruiter_bp, url_prefix='/api/recruiter')

    return app