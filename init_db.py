from flask import Flask
from auth import db, User

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db.init_app(app)

with app.app_context():
    db.create_all()
    
    # Check if user already exists
    existing_user = User.query.filter_by(username="admin").first()
    if not existing_user:
        user = User(username="admin", password="password")
        db.session.add(user)
        db.session.commit()
        print("User 'admin' created with password 'password'")
    else:
        print("User 'admin' already exists")