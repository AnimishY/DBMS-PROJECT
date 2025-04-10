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
    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed')
            return redirect(url_for('buyer.login'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT ProductId, Name, Description, Price, Stock, image_path FROM Product')
        products = cursor.fetchall()
        return render_template('buyer_dashboard.html', buyer_name=session.get('buyer_name'), products=products)
    except Exception as e:
        flash(f'Failed to load dashboard: {str(e)}')
        return redirect(url_for('buyer.login'))
    finally:
        if conn:
            conn.close()

@buyer_blueprint.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully')
    return redirect(url_for('home'))

@buyer_blueprint.route('/products')
@login_required
def products():
    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed')
            return redirect(url_for('buyer.dashboard'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT ProductId, Name, Description, Price, Stock, image_path FROM Product')
        products = cursor.fetchall()
        return render_template('buyer_dashboard.html', buyer_name=session.get('buyer_name'), products=products)
    except Exception as e:
        flash(f'Failed to load products: {str(e)}')
        return redirect(url_for('buyer.dashboard'))
    finally:
        if conn:
            conn.close()

@buyer_blueprint.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    quantity = int(request.form['quantity'])
    buyer_id = session['buyer_id']

    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed')
            return redirect(url_for('buyer.products'))

        cursor = conn.cursor(dictionary=True)

        # Check if the buyer has a cart
        cursor.execute('SELECT CartId FROM Cart WHERE BuyerId = %s', (buyer_id,))
        cart = cursor.fetchone()

        if not cart:
            cursor.execute('INSERT INTO Cart (BuyerId) VALUES (%s)', (buyer_id,))
            conn.commit()
            cart_id = cursor.lastrowid
        else:
            cart_id = cart['CartId']

        # Add product to cart
        cursor.execute('''
            INSERT INTO CartItem (CartId, ProductId, Quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE Quantity = Quantity + %s
        ''', (cart_id, product_id, quantity, quantity))
        conn.commit()

        flash('Product added to cart successfully!')
        return redirect(url_for('buyer.products'))
    except Exception as e:
        flash(f'Failed to add product to cart: {str(e)}')
        return redirect(url_for('buyer.products'))
    finally:
        if conn:
            conn.close()

@buyer_blueprint.route('/cart')
@login_required
def cart():
    buyer_id = session['buyer_id']

    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed')
            return redirect(url_for('buyer.dashboard'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT p.ProductId, p.Name, p.Description, p.Price, ci.Quantity
            FROM CartItem ci
            JOIN Product p ON ci.ProductId = p.ProductId
            JOIN Cart c ON ci.CartId = c.CartId
            WHERE c.BuyerId = %s
        ''', (buyer_id,))
        cart_items = cursor.fetchall()

        return render_template('buyer_cart.html', cart_items=cart_items)
    except Exception as e:
        flash(f'Failed to load cart: {str(e)}')
        return redirect(url_for('buyer.dashboard'))
    finally:
        if conn:
            conn.close()

@buyer_blueprint.route('/remove_from_cart/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    buyer_id = session['buyer_id']

    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed')
            return redirect(url_for('buyer.cart'))

        cursor = conn.cursor(dictionary=True)

        # Remove the product from the cart
        cursor.execute('''
            DELETE ci
            FROM CartItem ci
            JOIN Cart c ON ci.CartId = c.CartId
            WHERE c.BuyerId = %s AND ci.ProductId = %s
        ''', (buyer_id, product_id))
        conn.commit()

        flash('Product removed from cart successfully!')
        return redirect(url_for('buyer.cart'))
    except Exception as e:
        flash(f'Failed to remove product from cart: {str(e)}')
        return redirect(url_for('buyer.cart'))
    finally:
        if conn:
            conn.close()

@buyer_blueprint.route('/place_order', methods=['POST'])
@login_required
def place_order():
    buyer_id = session['buyer_id']

    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed')
            return redirect(url_for('buyer.cart'))

        cursor = conn.cursor(dictionary=True)

        # Fetch cart items and calculate total amount
        cursor.execute('''
            SELECT p.ProductId, p.Price, p.Stock, ci.Quantity
            FROM CartItem ci
            JOIN Product p ON ci.ProductId = p.ProductId
            JOIN Cart c ON ci.CartId = c.CartId
            WHERE c.BuyerId = %s
        ''', (buyer_id,))
        cart_items = cursor.fetchall()

        if not cart_items:
            flash('Your cart is empty')
            return redirect(url_for('buyer.cart'))

        total_amount = 0
        for item in cart_items:
            if item['Quantity'] > item['Stock']:
                flash(f"Insufficient stock for product: {item['ProductId']}")
                return redirect(url_for('buyer.cart'))
            total_amount += item['Price'] * item['Quantity']

        # Insert order
        cursor.execute('''
            INSERT INTO Orders (BuyerId, TotalAmount, OrderStatus)
            VALUES (%s, %s, %s)
        ''', (buyer_id, total_amount, 'Placed'))
        order_id = cursor.lastrowid

        # Insert order items and update product stock
        for item in cart_items:
            cursor.execute('''
                INSERT INTO OrderItem (OrderId, ProductId, Quantity, UnitPrice)
                VALUES (%s, %s, %s, %s)
            ''', (order_id, item['ProductId'], item['Quantity'], item['Price']))

            # Decrease stock
            cursor.execute('''
                UPDATE Product
                SET Stock = Stock - %s
                WHERE ProductId = %s
            ''', (item['Quantity'], item['ProductId']))

        # Clear cart
        cursor.execute('''
            DELETE ci
            FROM CartItem ci
            JOIN Cart c ON ci.CartId = c.CartId
            WHERE c.BuyerId = %s
        ''', (buyer_id,))

        conn.commit()
        flash('Order placed successfully!')
        return redirect(url_for('buyer.order_placed'))
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Failed to place order: {str(e)}')
        return redirect(url_for('buyer.cart'))
    finally:
        if conn:
            conn.close()

@buyer_blueprint.route('/order_placed')
@login_required
def order_placed():
    return render_template('order_placed.html')

@buyer_blueprint.route('/order_history')
@login_required
def order_history():
    buyer_id = session['buyer_id']

    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed')
            return redirect(url_for('buyer.dashboard'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT OrderId, OrderDate, TotalAmount, OrderStatus
            FROM Orders
            WHERE BuyerId = %s
            ORDER BY OrderDate DESC
        ''', (buyer_id,))
        orders = cursor.fetchall()

        return render_template('order_history.html', orders=orders)
    except Exception as e:
        flash(f'Failed to load order history: {str(e)}')
        return redirect(url_for('buyer.dashboard'))
    finally:
        if conn:
            conn.close()