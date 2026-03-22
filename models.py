from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()

# Many-to-Many association for Workouts and Exercises
workout_exercises = db.Table('workout_exercises',
    db.Column('workout_id', db.Integer, db.ForeignKey('workout.id'), primary_key=True),
    db.Column('exercise_id', db.Integer, db.ForeignKey('exercise.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='Admin') # Admin, Trainer

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
    diet_plans = db.relationship('DietPlan', backref='member', lazy=True)
    workout_assignments = db.relationship('WorkoutAssignment', backref='member', lazy=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False) # Cash, Card, Online

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    condition = db.Column(db.String(50), default='Good') # Good, Needs Repair, Broken
    last_maintenance = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    location = db.Column(db.String(100), nullable=True)

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    hire_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Trainer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    classes = db.relationship('GymClass', backref='trainer', lazy=True)

class GymClass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainer.id'), nullable=False)
    schedule_time = db.Column(db.String(50), nullable=False) # e.g. Mon 10:00 AM
    capacity = db.Column(db.Integer, nullable=False)
    bookings = db.relationship('Booking', backref='gym_class', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    gym_class_id = db.Column(db.Integer, db.ForeignKey('gym_class.id'), nullable=False)
    booking_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    member_ref = db.relationship('Member', backref='bookings_list', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    product = db.relationship('Product', backref='sales', lazy=True)

class MemberProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    weight = db.Column(db.Float, nullable=True)
    height = db.Column(db.Float, nullable=True)
    bmi = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    record_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    member = db.relationship('Member', backref='progress_records', lazy=True)

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False) # Cardio, Strength, etc.

class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    exercises = db.relationship('Exercise', secondary=workout_exercises, backref='workouts', lazy='dynamic')

class WorkoutAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workout.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    workout = db.relationship('Workout', backref='assignments', lazy=True)

class DietPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages', lazy=True)
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    check_in_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
