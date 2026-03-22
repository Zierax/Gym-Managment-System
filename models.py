from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class MembershipPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    members = db.relationship('Member', backref='plan', lazy=True)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=True)
    membership_plan_id = db.Column(db.Integer, db.ForeignKey('membership_plan.id'), nullable=False)
    join_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expiry_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Active') # Active, Expired, Inactive
    payments = db.relationship('Payment', backref='member', lazy=True)
    attendance = db.relationship('Attendance', backref='member', lazy=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False) # Cash, Card, Online

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    check_in_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
