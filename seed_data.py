from app import app
from models import db, User, MembershipPlan, Member, Payment, Attendance
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash

def seed():
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()

        # Create Admin User
        admin = User(username='admin', password=generate_password_hash('password123'))
        db.session.add(admin)

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
        db.session.commit()

        # Create Attendance
        a1 = Attendance(member_id=m1.id)
        db.session.add(a1)
        db.session.commit()

        print("Database seeded successfully!")

if __name__ == '__main__':
    seed()
