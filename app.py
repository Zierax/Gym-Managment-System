from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Member, MembershipPlan, Payment, Attendance
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

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
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
        'expiring_soon': expiring_soon
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
    for plan in plans:
        count = len(plan.members)
        revenue = sum(p.amount for m in plan.members for p in m.payments)
        popular_plans.append({
            'name': plan.name,
            'count': count,
            'revenue': revenue
        })

    return render_template('dashboard.html', stats=stats, recent_activities=recent_activities, popular_plans=popular_plans)

@app.route('/members')
@login_required
def members():
    members_list = Member.query.all()
    return render_template('members.html', members=members_list)

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

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
