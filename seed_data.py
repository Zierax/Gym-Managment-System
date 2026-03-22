from app import app
from models import db, User, MembershipPlan, Member, Payment, Attendance, Trainer, GymClass, Booking, Equipment, Staff, Exercise, Workout, Product, Message
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash

def seed():
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()

        # Create Users
        admin = User(username='admin', password=generate_password_hash('password123'), role='Admin')
        trainer_user = User(username='trainer1', password=generate_password_hash('trainer123'), role='Trainer')
        db.session.add_all([admin, trainer_user])

        # Create Membership Plans
        plans = [
            MembershipPlan(name='Basic Monthly', price=30.0, duration_days=30),
            MembershipPlan(name='Gold Quarterly', price=80.0, duration_days=90),
            MembershipPlan(name='Platinum Annual', price=300.0, duration_days=365)
        ]
        db.session.add_all(plans)
        db.session.commit()

        # Create Members
        m1 = Member(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='1234567890',
            address='123 Main St',
            membership_plan_id=plans[0].id,
            expiry_date=datetime.now(timezone.utc) + timedelta(days=30)
        )
        m2 = Member(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            phone='0987654321',
            address='456 Oak Ave',
            membership_plan_id=plans[1].id,
            expiry_date=datetime.now(timezone.utc) + timedelta(days=90)
        )
        db.session.add_all([m1, m2])
        db.session.commit()

        # Create Payments
        p1 = Payment(member_id=m1.id, amount=30.0, payment_method='Cash')
        p2 = Payment(member_id=m2.id, amount=80.0, payment_method='Card')
        db.session.add_all([p1, p2])

        # Create Attendance
        a1 = Attendance(member_id=m1.id)
        db.session.add(a1)

        # Create Trainers
        t1 = Trainer(name='Mike Strong', specialty='Bodybuilding', bio='Ex-pro bodybuilder with 10 years experience.')
        t2 = Trainer(name='Sarah Flow', specialty='Yoga', bio='Certified Yoga instructor focusing on mindfulness.')
        db.session.add_all([t1, t2])
        db.session.commit()

        # Create Gym Classes
        c1 = GymClass(name='Power Lifting', trainer_id=t1.id, schedule_time='Mon, Wed 6:00 PM', capacity=10)
        c2 = GymClass(name='Zen Yoga', trainer_id=t2.id, schedule_time='Tue, Thu 8:00 AM', capacity=20)
        db.session.add_all([c1, c2])
        db.session.commit()

        # Create Bookings
        b1 = Booking(member_id=m1.id, gym_class_id=c1.id)
        b2 = Booking(member_id=m2.id, gym_class_id=c2.id)
        db.session.add_all([b1, b2])

        # Create Equipment
        e1 = Equipment(name='Treadmill T80', condition='Good', location='Cardio Zone')
        e2 = Equipment(name='Power Rack', condition='Good', location='Weight Area')
        e3 = Equipment(name='Stationary Bike', condition='Needs Repair', location='Cardio Zone')
        db.session.add_all([e1, e2, e3])

        # Create Staff
        s1 = Staff(name='Robert Manager', role='General Manager', phone='555-0101')
        s2 = Staff(name='Alice Reception', role='Receptionist', phone='555-0102')
        db.session.add_all([s1, s2])

        # Exercises
        ex1 = Exercise(name='Bench Press', category='Strength', description='Chest exercise')
        ex2 = Exercise(name='Squat', category='Strength', description='Leg exercise')
        ex3 = Exercise(name='Running', category='Cardio', description='Treadmill run')
        db.session.add_all([ex1, ex2, ex3])
        db.session.commit()

        # Workouts
        w1 = Workout(title='Full Body Strength', description='Basic strength routine')
        w1.exercises.append(ex1)
        w1.exercises.append(ex2)
        db.session.add(w1)

        # Products
        prod1 = Product(name='Whey Protein', price=50.0, stock=20)
        prod2 = Product(name='Energy Drink', price=3.5, stock=50)
        db.session.add_all([prod1, prod2])

        # Messages
        msg1 = Message(sender_id=admin.id, receiver_id=trainer_user.id, content='Hello Trainer, welcome to the system!')
        db.session.add(msg1)

        db.session.commit()
        print("Database seeded with comprehensive data successfully!")

if __name__ == '__main__':
    seed()
