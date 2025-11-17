from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import db
from models import User
from werkzeug.security import generate_password_hash, check_password_hash
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        # Validate empty fields
        if not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return redirect(url_for('auth.signup'))

        # Validate email
        if not is_valid_email(email):
            flash("Invalid email format.", "danger")
            return redirect(url_for('auth.signup'))

        # Confirm password
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('auth.signup'))

        # Check password strength (optional)
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return redirect(url_for('auth.signup'))

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.signup'))

        # Create new user
        new_user = User(
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Signup successful! You can now login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('signup.html', active='signup')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html', active='login')


@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('auth.login'))
