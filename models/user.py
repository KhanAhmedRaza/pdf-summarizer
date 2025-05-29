from flask_login import UserMixin
from datetime import datetime
from extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    profile_pic = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.email}>'

 # Plan information
    plan_type = db.Column(db.String(20), default="free")  # free, starter, pro
    plan_start_date = db.Column(db.DateTime, default=datetime.utcnow)
    plan_end_date = db.Column(db.DateTime)