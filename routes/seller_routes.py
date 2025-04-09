from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from config.database import connect_to_mysql
from functools import wraps

seller_blueprint = Blueprint('seller', __name__)

def seller_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'seller_id' not in session:
            flash('Please login first')
            return redirect(url_for('seller.login'))
        return f(*args, **kwargs)
    return decorated_function

@seller_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        store_name = request.form['store_name']
        contact = request.form['contact']
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
                return redirect(url_for('seller.register'))
                
            cursor = conn.cursor(dictionary=True, buffered=True)
            
            # Check if email already exists
            check_query = 'SELECT Email FROM Seller WHERE Email = %s'
            cursor.execute(check_query, (email,))
            if cursor.fetchone():
                flash('Email already registered')
                return redirect(url_for('seller.register'))
            
            # Insert new seller with explicit column names
            insert_query = '''
                INSERT INTO Seller (StoreName, SellerContact, Email, PasswordHash, 
                    StoreAddressLine1, StoreAddressLine2, City, States, PinCode) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            values = (store_name, contact, email, generate_password_hash(password),
                     address_line1, address_line2, city, state, pincode)
            
            cursor.execute(insert_query, values)
            conn.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('seller.login'))
            
        except Exception as e:
            print(f"Database error during registration: {str(e)}")
            if conn:
                conn.rollback()
            flash(f'Registration failed: {str(e)}')
            return redirect(url_for('seller.register'))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('seller_register.html')

@seller_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = None
        try:
            conn = connect_to_mysql()
            if not conn:
                flash('Database connection failed')
                return redirect(url_for('seller.login'))

            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute('SELECT * FROM Seller WHERE Email = %s', (email,))
            seller = cursor.fetchone()

            if seller and check_password_hash(seller['PasswordHash'], password):
                session['seller_id'] = seller['SellerId']
                session['store_name'] = seller['StoreName']
                flash('Login successful!')
                return redirect(url_for('seller.dashboard'))
            
            flash('Invalid email or password')
            return redirect(url_for('seller.login'))
            
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash(f'Login failed: {str(e)}')
            return redirect(url_for('seller.login'))
        finally:
            if conn:
                conn.close()

    return render_template('seller_login.html')

@seller_blueprint.route('/dashboard')
@seller_login_required
def dashboard():
    return render_template('seller_dashboard.html', store_name=session.get('store_name'))

@seller_blueprint.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully')
    return redirect(url_for('home'))