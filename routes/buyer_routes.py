from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config.database import connect_to_mysql

buyer_blueprint = Blueprint('buyer', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'buyer_id' not in session:
            flash('Please login first')
            return redirect(url_for('buyer.login'))
        return f(*args, **kwargs)
    return decorated_function

@buyer_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        address_line1 = request.form['address_line1']
        address_line2 = request.form.get('address_line2')
        city = request.form['city']
        state = request.form['state']
        pincode = request.form['pincode']

        conn = None
        try:
            conn = connect_to_mysql()
            if not conn:
                flash('Database connection failed')
                return redirect(url_for('buyer.register'))
                
            cursor = conn.cursor(dictionary=True, buffered=True)
            
            # Check if email already exists
            check_query = 'SELECT Email FROM Buyer WHERE Email = %s'
            cursor.execute(check_query, (email,))
            if cursor.fetchone():
                flash('Email already registered')
                return redirect(url_for('buyer.register'))
            
            # Insert new buyer
            insert_query = '''INSERT INTO Buyer 
                (BuyerFirstName, BuyerLastName, Email, PasswordHash, 
                AddressLine1, AddressLine2, City, States, PinCode) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)'''
            values = (first_name, last_name, email, generate_password_hash(password),
                     address_line1, address_line2, city, state, pincode)
            
            cursor.execute(insert_query, values)
            conn.commit()
            
            flash('Registration successful! Please login.')
            return redirect(url_for('buyer.login'))
            
        except Exception as e:
            print(f"Database error during registration: {str(e)}")
            if conn:
                conn.rollback()
            flash(f'Registration failed: {str(e)}')
            return redirect(url_for('buyer.register'))
        finally:
            if conn:
                conn.close()

    return render_template('buyer_register.html')

@buyer_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = None
        try:
            conn = connect_to_mysql()
            if not conn:
                flash('Database connection failed')
                return redirect(url_for('buyer.login'))

            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM Buyer WHERE Email = %s', (email,))
            buyer = cursor.fetchone()

            if buyer and check_password_hash(buyer['PasswordHash'], password):
                session['buyer_id'] = buyer['BuyerId']
                session['buyer_name'] = f"{buyer['BuyerFirstName']} {buyer['BuyerLastName']}"
                flash('Login successful!')
                return redirect(url_for('buyer.dashboard'))
            
            flash('Invalid email or password')
            return redirect(url_for('buyer.login'))
        except Exception as e:
            flash(f'Login failed: {str(e)}')
            return redirect(url_for('buyer.login'))
        finally:
            if conn:
                conn.close()

    return render_template('buyer_login.html')  # Changed from login.html to buyer_login.html

@buyer_blueprint.route('/dashboard')
@login_required
def dashboard():
    return render_template('buyer_dashboard.html', buyer_name=session.get('buyer_name'))

@buyer_blueprint.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully')
    return redirect(url_for('home'))