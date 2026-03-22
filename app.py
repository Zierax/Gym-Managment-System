import csv
import io
from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, flash, Response, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Member, MembershipPlan, Payment, Attendance, Trainer, GymClass, Booking, Equipment, Staff, Exercise, Workout, WorkoutAssignment, DietPlan, Message, MemberProgress, Product, Sale
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gym-management-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'Admin':
            flash('Access denied: Admin only.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def update_member_statuses():
    now = datetime.now(timezone.utc)
    expired_members = Member.query.filter(Member.expiry_date < now, Member.status == 'Active').all()
    for member in expired_members:
        member.status = 'Expired'
    db.session.commit()

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    update_member_statuses()
    total_members = Member.query.count()
    active_members = Member.query.filter_by(status='Active').count()

    # Simple monthly revenue calculation
    now = datetime.now(timezone.utc)
    this_month_payments = Payment.query.filter(Payment.payment_date >= datetime(now.year, now.month, 1, tzinfo=timezone.utc)).all()
    monthly_revenue = sum(p.amount for p in this_month_payments)

    # Expiring soon (within 7 days)
    expiring_soon = Member.query.filter(
        Member.status == 'Active',
        Member.expiry_date <= now + timedelta(days=7)
    ).count()

    stats = {
        'total_members': total_members,
        'active_members': active_members,
        'monthly_revenue': monthly_revenue,
        'expiring_soon': expiring_soon,
        'total_trainers': Trainer.query.count(),
        'active_classes': GymClass.query.count(),
        'inventory_count': Product.query.count()
    }

    # Recent Activities (mocking for now with some real data)
    recent_payments = Payment.query.order_by(Payment.payment_date.desc()).limit(5).all()
    recent_activities = []
    for p in recent_payments:
        recent_activities.append({
            'icon': 'fa-credit-card',
            'text': f'Payment of ${p.amount} from {p.member.first_name} {p.member.last_name}',
            'time': p.payment_date.strftime('%Y-%m-%d %H:%M')
        })

    # Popular plans
    plans = MembershipPlan.query.all()
    popular_plans = []
    plan_names = []
    plan_member_counts = []
    for plan in plans:
        count = len(plan.members)
        revenue = sum(p.amount for m in plan.members for p in m.payments)
        popular_plans.append({
            'name': plan.name,
            'count': count,
            'revenue': revenue
        })
        plan_names.append(plan.name)
        plan_member_counts.append(count)

    # Revenue data for the last 6 months (mocking for simplicity)
    revenue_labels = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
    revenue_values = [1200, 1500, 1100, 1800, 2100, monthly_revenue]

    return render_template('dashboard.html',
                         stats=stats,
                         recent_activities=recent_activities,
                         popular_plans=popular_plans,
                         plan_names=plan_names,
                         plan_member_counts=plan_member_counts,
                         revenue_labels=revenue_labels,
                         revenue_values=revenue_values)

@app.route('/members')
@login_required
def members():
    search = request.args.get('search')
    if search:
        members_list = Member.query.filter(
            (Member.first_name.like(f'%{search}%')) |
            (Member.last_name.like(f'%{search}%')) |
            (Member.email.like(f'%{search}%'))
        ).all()
    else:
        members_list = Member.query.all()
    return render_template('members.html', members=members_list)

@app.route('/member/<int:id>')
@login_required
def member_detail(id):
    member = Member.query.get_or_404(id)
    return render_template('member_detail.html', member=member)

@app.route('/member/renew/<int:id>', methods=['GET', 'POST'])
@login_required
def renew_member(id):
    member = Member.query.get_or_404(id)
    plans = MembershipPlan.query.all()
    if request.method == 'POST':
        plan_id = request.form.get('plan_id')
        payment_method = request.form.get('payment_method')
        plan = MembershipPlan.query.get(plan_id)

        # Update expiry date
        if member.expiry_date > datetime.now(timezone.utc):
            member.expiry_date += timedelta(days=plan.duration_days)
        else:
            member.expiry_date = datetime.now(timezone.utc) + timedelta(days=plan.duration_days)

        member.membership_plan_id = plan_id
        member.status = 'Active'

        # Record payment
        new_payment = Payment(member_id=member.id, amount=plan.price, payment_method=payment_method)
        db.session.add(new_payment)
        db.session.commit()

        flash(f'Membership renewed for {member.first_name}!', 'success')
        return redirect(url_for('member_detail', id=member.id))
    return render_template('renew_member.html', member=member, plans=plans)

@app.route('/payment/invoice/<int:id>')
@login_required
def view_invoice(id):
    payment = Payment.query.get_or_404(id)
    return render_template('invoice.html', payment=payment)

@app.route('/member/add', methods=['GET', 'POST'])
@login_required
def add_member():
    plans = MembershipPlan.query.all()
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        plan_id = request.form.get('plan_id')

        plan = MembershipPlan.query.get(plan_id)
        expiry_date = datetime.now(timezone.utc) + timedelta(days=plan.duration_days)

        new_member = Member(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            address=address,
            membership_plan_id=plan_id,
            expiry_date=expiry_date
        )
        db.session.add(new_member)
        db.session.commit()
        flash('Member added successfully!', 'success')
        return redirect(url_for('members'))
    return render_template('member_form.html', plans=plans, title="Add Member")

@app.route('/member/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_member(id):
    member = Member.query.get_or_404(id)
    plans = MembershipPlan.query.all()
    if request.method == 'POST':
        member.first_name = request.form.get('first_name')
        member.last_name = request.form.get('last_name')
        member.email = request.form.get('email')
        member.phone = request.form.get('phone')
        member.address = request.form.get('address')
        member.membership_plan_id = request.form.get('plan_id')
        member.status = request.form.get('status')

        db.session.commit()
        flash('Member updated successfully!', 'success')
        return redirect(url_for('members'))
    return render_template('member_form.html', member=member, plans=plans, title="Edit Member")

@app.route('/member/delete/<int:id>')
@login_required
def delete_member(id):
    member = Member.query.get_or_404(id)
    db.session.delete(member)
    db.session.commit()
    flash('Member deleted successfully!', 'success')
    return redirect(url_for('members'))

@app.route('/members/export')
@login_required
def export_members():
    members_list = Member.query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Plan', 'Expiry Date', 'Status'])

    for m in members_list:
        writer.writerow([m.id, m.first_name, m.last_name, m.email, m.phone, m.plan.name, m.expiry_date.strftime('%Y-%m-%d'), m.status])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=members_export.csv"}
    )

@app.route('/plans')
@login_required
def plans():
    plans_list = MembershipPlan.query.all()
    return render_template('plans.html', plans=plans_list)

@app.route('/plan/add', methods=['GET', 'POST'])
@login_required
def add_plan():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        duration_days = request.form.get('duration_days')

        new_plan = MembershipPlan(name=name, price=float(price), duration_days=int(duration_days))
        db.session.add(new_plan)
        db.session.commit()
        flash('Plan added successfully!', 'success')
        return redirect(url_for('plans'))
    return render_template('plan_form.html', title="Add Plan")

@app.route('/plan/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_plan(id):
    plan = MembershipPlan.query.get_or_404(id)
    if request.method == 'POST':
        plan.name = request.form.get('name')
        plan.price = float(request.form.get('price'))
        plan.duration_days = int(request.form.get('duration_days'))

        db.session.commit()
        flash('Plan updated successfully!', 'success')
        return redirect(url_for('plans'))
    return render_template('plan_form.html', plan=plan, title="Edit Plan")

@app.route('/plan/delete/<int:id>')
@login_required
def delete_plan(id):
    plan = MembershipPlan.query.get_or_404(id)
    if plan.members:
        flash('Cannot delete plan with active members!', 'danger')
    else:
        db.session.delete(plan)
        db.session.commit()
        flash('Plan deleted successfully!', 'success')
    return redirect(url_for('plans'))

@app.route('/payments')
@login_required
def payments():
    payments_list = Payment.query.order_by(Payment.payment_date.desc()).all()
    return render_template('payments.html', payments=payments_list)

@app.route('/payment/add', methods=['GET', 'POST'])
@login_required
def add_payment():
    members_list = Member.query.all()
    if request.method == 'POST':
        member_id = request.form.get('member_id')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')

        new_payment = Payment(
            member_id=member_id,
            amount=float(amount),
            payment_method=payment_method
        )
        db.session.add(new_payment)
        db.session.commit()
        flash('Payment recorded successfully!', 'success')
        return redirect(url_for('payments'))
    return render_template('payment_form.html', members=members_list, title="Record Payment")

@app.route('/attendance')
@login_required
def attendance():
    attendance_list = Attendance.query.order_by(Attendance.check_in_time.desc()).all()
    members_list = Member.query.all()
    return render_template('attendance.html', attendance=attendance_list, members=members_list)

@app.route('/attendance/check-in', methods=['POST'])
@login_required
def check_in():
    member_id = request.form.get('member_id')
    new_attendance = Attendance(member_id=member_id)
    db.session.add(new_attendance)
    db.session.commit()
    flash('Attendance recorded!', 'success')
    return redirect(url_for('attendance'))

# Trainer Management
@app.route('/trainers')
@login_required
def trainers():
    trainers_list = Trainer.query.all()
    return render_template('trainers.html', trainers=trainers_list)

@app.route('/trainer/add', methods=['GET', 'POST'])
@login_required
def add_trainer():
    if request.method == 'POST':
        name = request.form.get('name')
        specialty = request.form.get('specialty')
        bio = request.form.get('bio')
        new_trainer = Trainer(name=name, specialty=specialty, bio=bio)
        db.session.add(new_trainer)
        db.session.commit()
        flash('Trainer added successfully!', 'success')
        return redirect(url_for('trainers'))
    return render_template('trainer_form.html', title="Add Trainer")

@app.route('/trainer/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_trainer(id):
    trainer = Trainer.query.get_or_404(id)
    if request.method == 'POST':
        trainer.name = request.form.get('name')
        trainer.specialty = request.form.get('specialty')
        trainer.bio = request.form.get('bio')
        db.session.commit()
        flash('Trainer updated successfully!', 'success')
        return redirect(url_for('trainers'))
    return render_template('trainer_form.html', trainer=trainer, title="Edit Trainer")

@app.route('/trainer/delete/<int:id>')
@login_required
def delete_trainer(id):
    trainer = Trainer.query.get_or_404(id)
    if trainer.classes:
        flash('Cannot delete trainer with assigned classes!', 'danger')
    else:
        db.session.delete(trainer)
        db.session.commit()
        flash('Trainer deleted successfully!', 'success')
    return redirect(url_for('trainers'))

# Gym Class Management
@app.route('/classes')
@login_required
def classes():
    classes_list = GymClass.query.all()
    return render_template('classes.html', classes=classes_list)

@app.route('/class/add', methods=['GET', 'POST'])
@login_required
def add_class():
    trainers_list = Trainer.query.all()
    if request.method == 'POST':
        name = request.form.get('name')
        trainer_id = request.form.get('trainer_id')
        schedule_time = request.form.get('schedule_time')
        capacity = request.form.get('capacity')
        new_class = GymClass(name=name, trainer_id=trainer_id, schedule_time=schedule_time, capacity=int(capacity))
        db.session.add(new_class)
        db.session.commit()
        flash('Class added successfully!', 'success')
        return redirect(url_for('classes'))
    return render_template('class_form.html', trainers=trainers_list, title="Add Class")

@app.route('/class/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_class(id):
    gym_class = GymClass.query.get_or_404(id)
    trainers_list = Trainer.query.all()
    if request.method == 'POST':
        gym_class.name = request.form.get('name')
        gym_class.trainer_id = request.form.get('trainer_id')
        gym_class.schedule_time = request.form.get('schedule_time')
        gym_class.capacity = int(request.form.get('capacity'))
        db.session.commit()
        flash('Class updated successfully!', 'success')
        return redirect(url_for('classes'))
    return render_template('class_form.html', gym_class=gym_class, trainers=trainers_list, title="Edit Class")

@app.route('/class/delete/<int:id>')
@login_required
def delete_class(id):
    gym_class = GymClass.query.get_or_404(id)
    if gym_class.bookings:
        flash('Cannot delete class with active bookings!', 'danger')
    else:
        db.session.delete(gym_class)
        db.session.commit()
        flash('Class deleted successfully!', 'success')
    return redirect(url_for('classes'))

# Class Booking
@app.route('/bookings')
@login_required
def bookings():
    bookings_list = Booking.query.order_by(Booking.booking_time.desc()).all()
    members_list = Member.query.all()
    classes_list = GymClass.query.all()
    return render_template('bookings.html', bookings=bookings_list, members=members_list, classes=classes_list)

@app.route('/booking/add', methods=['POST'])
@login_required
def add_booking():
    member_id = request.form.get('member_id')
    class_id = request.form.get('class_id')

    gym_class = GymClass.query.get(class_id)
    if len(gym_class.bookings) >= gym_class.capacity:
        flash('Class is already at full capacity!', 'danger')
    else:
        new_booking = Booking(member_id=member_id, gym_class_id=class_id)
        db.session.add(new_booking)
        db.session.commit()
        flash('Booking successful!', 'success')
    return redirect(url_for('bookings'))

@app.route('/booking/delete/<int:id>')
@login_required
def delete_booking(id):
    booking = Booking.query.get_or_404(id)
    db.session.delete(booking)
    db.session.commit()
    flash('Booking cancelled!', 'success')
    return redirect(url_for('bookings'))

# Equipment Management
@app.route('/equipment')
@login_required
def equipment():
    equipment_list = Equipment.query.all()
    return render_template('equipment.html', equipment=equipment_list)

@app.route('/equipment/add', methods=['GET', 'POST'])
@login_required
def add_equipment():
    if request.method == 'POST':
        name = request.form.get('name')
        condition = request.form.get('condition')
        location = request.form.get('location')
        new_item = Equipment(name=name, condition=condition, location=location)
        db.session.add(new_item)
        db.session.commit()
        flash('Equipment added successfully!', 'success')
        return redirect(url_for('equipment'))
    return render_template('equipment_form.html', title="Add Equipment")

@app.route('/equipment/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_equipment(id):
    item = Equipment.query.get_or_404(id)
    if request.method == 'POST':
        item.name = request.form.get('name')
        item.condition = request.form.get('condition')
        item.location = request.form.get('location')
        db.session.commit()
        flash('Equipment updated successfully!', 'success')
        return redirect(url_for('equipment'))
    return render_template('equipment_form.html', item=item, title="Edit Equipment")

@app.route('/equipment/delete/<int:id>')
@login_required
def delete_equipment(id):
    item = Equipment.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Equipment removed!', 'success')
    return redirect(url_for('equipment'))

# Staff Management
@app.route('/staff')
@login_required
@admin_required
def staff():
    staff_list = Staff.query.all()
    return render_template('staff.html', staff=staff_list)

@app.route('/staff/add', methods=['GET', 'POST'])
@login_required
def add_staff():
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        phone = request.form.get('phone')
        new_staff = Staff(name=name, role=role, phone=phone)
        db.session.add(new_staff)
        db.session.commit()
        flash('Staff added successfully!', 'success')
        return redirect(url_for('staff'))
    return render_template('staff_form.html', title="Add Staff")

@app.route('/staff/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_staff(id):
    staff_member = Staff.query.get_or_404(id)
    if request.method == 'POST':
        staff_member.name = request.form.get('name')
        staff_member.role = request.form.get('role')
        staff_member.phone = request.form.get('phone')
        db.session.commit()
        flash('Staff updated successfully!', 'success')
        return redirect(url_for('staff'))
    return render_template('staff_form.html', staff=staff_member, title="Edit Staff")

@app.route('/staff/delete/<int:id>')
@login_required
def delete_staff(id):
    staff_member = Staff.query.get_or_404(id)
    db.session.delete(staff_member)
    db.session.commit()
    flash('Staff member removed!', 'success')
    return redirect(url_for('staff'))

# Exercise Management
@app.route('/exercises')
@login_required
def exercises():
    exercises_list = Exercise.query.all()
    return render_template('exercises.html', exercises=exercises_list)

@app.route('/exercise/add', methods=['GET', 'POST'])
@login_required
def add_exercise():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        new_exercise = Exercise(name=name, description=description, category=category)
        db.session.add(new_exercise)
        db.session.commit()
        flash('Exercise added successfully!', 'success')
        return redirect(url_for('exercises'))
    return render_template('exercise_form.html', title="Add Exercise")

@app.route('/exercise/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_exercise(id):
    exercise = Exercise.query.get_or_404(id)
    if request.method == 'POST':
        exercise.name = request.form.get('name')
        exercise.description = request.form.get('description')
        exercise.category = request.form.get('category')
        db.session.commit()
        flash('Exercise updated successfully!', 'success')
        return redirect(url_for('exercises'))
    return render_template('exercise_form.html', exercise=exercise, title="Edit Exercise")

@app.route('/exercise/delete/<int:id>')
@login_required
def delete_exercise(id):
    exercise = Exercise.query.get_or_404(id)
    db.session.delete(exercise)
    db.session.commit()
    flash('Exercise deleted!', 'success')
    return redirect(url_for('exercises'))

# Workout Templates
@app.route('/workouts')
@login_required
def workouts():
    workouts_list = Workout.query.all()
    return render_template('workouts.html', workouts=workouts_list)

@app.route('/workout/add', methods=['GET', 'POST'])
@login_required
def add_workout():
    exercises_list = Exercise.query.all()
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        selected_exercises = request.form.getlist('exercises')

        new_workout = Workout(title=title, description=description)
        for ex_id in selected_exercises:
            ex = Exercise.query.get(ex_id)
            new_workout.exercises.append(ex)

        db.session.add(new_workout)
        db.session.commit()
        flash('Workout template created!', 'success')
        return redirect(url_for('workouts'))
    return render_template('workout_form.html', exercises=exercises_list, title="Add Workout Template")

# Workout Assignments
@app.route('/assignments')
@login_required
def assignments():
    assignments_list = WorkoutAssignment.query.all()
    members_list = Member.query.all()
    workouts_list = Workout.query.all()
    return render_template('assignments.html', assignments=assignments_list, members=members_list, workouts=workouts_list)

@app.route('/assignment/add', methods=['POST'])
@login_required
def add_assignment():
    member_id = request.form.get('member_id')
    workout_id = request.form.get('workout_id')
    new_assignment = WorkoutAssignment(member_id=member_id, workout_id=workout_id)
    db.session.add(new_assignment)
    db.session.commit()
    flash('Workout assigned to member!', 'success')
    return redirect(url_for('assignments'))

# Diet Plans
@app.route('/diet-plans')
@login_required
def diet_plans():
    diets = DietPlan.query.all()
    members_list = Member.query.all()
    return render_template('diet_plans.html', diets=diets, members=members_list)

@app.route('/diet-plan/add', methods=['POST'])
@login_required
def add_diet_plan():
    title = request.form.get('title')
    description = request.form.get('description')
    member_id = request.form.get('member_id')
    new_diet = DietPlan(title=title, description=description, member_id=member_id)
    db.session.add(new_diet)
    db.session.commit()
    flash('Diet plan created!', 'success')
    return redirect(url_for('diet_plans'))

# Shop & Inventory
@app.route('/inventory')
@login_required
@admin_required
def inventory():
    products = Product.query.all()
    return render_template('inventory.html', products=products)

@app.route('/product/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        stock = request.form.get('stock')
        new_prod = Product(name=name, price=float(price), stock=int(stock))
        db.session.add(new_prod)
        db.session.commit()
        flash('Product added to inventory!', 'success')
        return redirect(url_for('inventory'))
    return render_template('product_form.html', title="Add Product")

@app.route('/sales')
@login_required
def sales():
    sales_list = Sale.query.order_by(Sale.sale_date.desc()).all()
    products = Product.query.all()
    members_list = Member.query.all()
    return render_template('sales.html', sales=sales_list, products=products, members=members_list)

@app.route('/sale/add', methods=['POST'])
@login_required
def add_sale():
    product_id = request.form.get('product_id')
    member_id = request.form.get('member_id')
    quantity = int(request.form.get('quantity'))

    product = Product.query.get(product_id)
    if product.stock < quantity:
        flash('Insufficient stock!', 'danger')
    else:
        total = product.price * quantity
        new_sale = Sale(product_id=product_id, member_id=member_id if member_id else None, quantity=quantity, total_price=total)
        product.stock -= quantity
        db.session.add(new_sale)
        db.session.commit()
        flash('Sale recorded!', 'success')
    return redirect(url_for('sales'))

# Fitness Progress
@app.route('/progress')
@login_required
def progress():
    members_list = Member.query.all()
    # If a specific member is requested via query param
    member_id = request.args.get('member_id')
    selected_member = None
    if member_id:
        selected_member = Member.query.get(member_id)
    return render_template('progress.html', members=members_list, selected_member=selected_member)

@app.route('/progress/add', methods=['POST'])
@login_required
def add_progress():
    member_id = request.form.get('member_id')
    weight = request.form.get('weight')
    height = request.form.get('height')
    notes = request.form.get('notes')

    # Calculate BMI
    bmi = None
    if weight and height:
        try:
            w = float(weight)
            h = float(height) / 100 # convert cm to m
            bmi = w / (h * h)
        except ZeroDivisionError:
            pass

    new_progress = MemberProgress(
        member_id=member_id,
        weight=float(weight) if weight else None,
        height=float(height) if height else None,
        bmi=bmi,
        notes=notes
    )
    db.session.add(new_progress)
    db.session.commit()
    flash('Progress record added!', 'success')
    return redirect(url_for('progress', member_id=member_id))

# Internal Messaging
@app.route('/messages', methods=['GET', 'POST'])
@login_required
def messages():
    users = User.query.filter(User.id != current_user.id).all()
    if request.method == 'POST':
        receiver_id = request.form.get('receiver_id')
        content = request.form.get('content')
        new_msg = Message(sender_id=current_user.id, receiver_id=receiver_id, content=content)
        db.session.add(new_msg)
        db.session.commit()
        flash('Message sent!', 'success')
        return redirect(url_for('messages'))

    received = Message.query.filter_by(receiver_id=current_user.id).order_by(Message.timestamp.desc()).all()
    sent = Message.query.filter_by(sender_id=current_user.id).order_by(Message.timestamp.desc()).all()
    return render_template('messages.html', users=users, received=received, sent=sent)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
