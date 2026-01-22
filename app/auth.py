from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json

bp = Blueprint('auth', __name__)

# Path to store user data
USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'users.json')

# Ensure users file exists (but don't create default admin)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({}, f)  # Start with empty users

class User(UserMixin):
    def __init__(self, username, is_admin=False):
        self.id = username
        self.username = username
        self.is_admin = is_admin
    
    @staticmethod
    def get(user_id):
        users = User.get_users()
        if user_id in users:
            user_data = users[user_id]
            return User(user_id, user_data.get('is_admin', False))
        return None
    
    @staticmethod
    def get_users():
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def save_users(users):
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=4)
    
    @staticmethod
    def add_user(username, password, is_admin=False):
        users = User.get_users()
        if username in users:
            return False
        
        users[username] = {
            "password": generate_password_hash(password),
            "is_admin": is_admin
        }
        User.save_users(users)
        return True
    
    @staticmethod
    def verify_password(username, password):
        users = User.get_users()
        if username in users and check_password_hash(users[username]["password"], password):
            return True
        return False

@bp.route('/login', methods=['GET', 'POST'])
def login():
    from flask import current_app
    limiter = getattr(current_app, 'limiter', None)

    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')

        if User.verify_password(username, password):
            user = User.get(username)
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.is_admin:
        flash('You do not have permission to register new users', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form
        
        if not username or not password:
            flash('Please fill in all fields', 'error')
            return render_template('register.html')
        
        if User.add_user(username, password, is_admin):
            flash(f'User {username} created successfully', 'success')
            return redirect(url_for('auth.register'))
        else:
            flash(f'User {username} already exists', 'error')
    
    users = User.get_users()
    return render_template('register.html', users=users)

@bp.route('/reset-password/<username>', methods=['POST'])
@login_required
def reset_password(username):
    if not current_user.is_admin:
        flash('You do not have permission to reset passwords', 'error')
        return redirect(url_for('main.index'))
    
    password = request.form.get('password')
    if not password:
        flash('Please provide a new password', 'error')
        return redirect(url_for('auth.register'))
    
    users = User.get_users()
    if username not in users:
        flash(f'User {username} does not exist', 'error')
        return redirect(url_for('auth.register'))
    
    users[username]['password'] = generate_password_hash(password)
    User.save_users(users)
    
    flash(f'Password for {username} has been reset', 'success')
    return redirect(url_for('auth.register'))

@bp.route('/delete-user/<username>', methods=['POST'])
@login_required
def delete_user(username):
    if not current_user.is_admin:
        flash('You do not have permission to delete users', 'error')
        return redirect(url_for('main.index'))
    
    if username == current_user.username:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('auth.register'))
    
    users = User.get_users()
    if username not in users:
        flash(f'User {username} does not exist', 'error')
        return redirect(url_for('auth.register'))
    
    del users[username]
    User.save_users(users)
    
    flash(f'User {username} has been deleted', 'success')
    return redirect(url_for('auth.register')) 