from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from .extensions import db

DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_TYPE'] = "filesystem"
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/auth')
    
    from .models import User, Service, Provider, ContactMessage

    with app.app_context():
        db.create_all()
        print("✅ Database and tables created successfully!")  # Debugging message

    # Configure Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.customer_login'  # Default login page
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        user_type = session.get("user_type")  # Fetch user type from session
        if user_type == "customer":
            return User.query.get(int(user_id))
        elif user_type == "provider":
            return Provider.query.get(int(user_id))
        return None  # If user not found

    return app
