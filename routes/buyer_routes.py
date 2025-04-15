import os
import json
import google.generativeai as genai
from flask import Flask, session
from flask_uploads import UploadSet, configure_uploads, IMAGES
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

        # Fetch top 5 most sold products
        top_products_query = '''
            SELECT p.ProductId, p.Name, p.Description, p.Price, p.Stock, p.image_path, 
                   SUM(oi.Quantity) AS total_sold
            FROM Product p
            JOIN OrderItem oi ON p.ProductId = oi.ProductId
            GROUP BY p.ProductId
            ORDER BY total_sold DESC
            LIMIT 5
        '''
        cursor.execute(top_products_query)
        top_products = cursor.fetchall()

        # Get filter and sort parameters from the request
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        sort = request.args.get('sort')

        # Build the query dynamically for all products
        query = 'SELECT ProductId, Name, Description, Price, Stock, image_path FROM Product WHERE 1=1'
        params = []

        if min_price is not None:
            query += ' AND Price >= %s'
            params.append(min_price)
        if max_price is not None:
            query += ' AND Price <= %s'
            params.append(max_price)

        # Add sorting logic
        if sort == 'name':
            query += ' ORDER BY Name ASC'
        elif sort == 'price':
            query += ' ORDER BY Price ASC'
        else:
            query += ' ORDER BY ProductId ASC'  # Default sorting

        cursor.execute(query, tuple(params))
        products = cursor.fetchall()

        return render_template('buyer_dashboard.html', buyer_name=session.get('buyer_name'), 
                               top_products=top_products, products=products)
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
                flash(f"Insufficient stock for product: {item['ProductId']} (Available: {item['Stock']}, Requested: {item['Quantity']})")
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
            SELECT o.OrderId, o.OrderDate, o.TotalAmount, o.OrderStatus,
                   s.ShipmentId, s.ShipmentDate, s.DeliveryDate, 
                   s.ShippingMethod, s.TrackingNumber 
            FROM Orders o
            LEFT JOIN Shipment s ON o.OrderId = s.OrderId
            WHERE o.BuyerId = %s
            ORDER BY o.OrderDate DESC
        ''', (buyer_id,))
        orders = cursor.fetchall()

        return render_template('order_history.html', orders=orders)
    except Exception as e:
        flash(f'Failed to load order history: {str(e)}')
        return redirect(url_for('buyer.dashboard'))
    finally:
        if conn:
            conn.close()

@buyer_blueprint.route('/track_order/<int:order_id>')
@login_required
def track_order(order_id):
    buyer_id = session['buyer_id']
    conn = None
    
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)
        
        # First verify this order belongs to the logged-in buyer
        cursor.execute('''
            SELECT o.OrderId FROM Orders o
            WHERE o.OrderId = %s AND o.BuyerId = %s
        ''', (order_id, buyer_id))
        
        if not cursor.fetchone():
            flash('Order not found or unauthorized access')
            return redirect(url_for('buyer.order_history'))
            
        # Get detailed tracking information
        cursor.execute('''
            SELECT o.OrderId, o.OrderDate, o.TotalAmount, o.OrderStatus,
                   s.ShipmentDate, s.DeliveryDate, s.ShippingMethod, s.TrackingNumber,
                   p.Name as ProductName, oi.Quantity, oi.UnitPrice
            FROM Orders o
            LEFT JOIN Shipment s ON o.OrderId = s.OrderId
            JOIN OrderItem oi ON o.OrderId = oi.OrderId
            JOIN Product p ON oi.ProductId = p.ProductId
            WHERE o.OrderId = %s
        ''', (order_id,))
        
        tracking_info = cursor.fetchall()
        
        if not tracking_info:
            flash('No details found for this order')
            return redirect(url_for('buyer.order_history'))
            
        return render_template('track_order.html', order_details=tracking_info)
        
    except Exception as e:
        flash(f'Failed to load tracking information: {str(e)}')
        return redirect(url_for('buyer.order_history'))
    finally:
        if conn:
            conn.close()

@buyer_blueprint.route('/ai_search', methods=['GET', 'POST'])
@login_required
def ai_search():
    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed')
            return redirect(url_for('buyer.dashboard'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT ProductId, Name, Description, Price, Stock, image_path FROM Product')
        products = cursor.fetchall()

        if request.method == 'POST':
            user_input = request.form.get('search_query', '').strip()
            if not user_input:
                flash('Please enter a search query.')
                return render_template('ai_search.html')

            try:
                # Configure API - use a hardcoded API key for now, replace with environment variable in production
                api_key = "AIzaSyC05dOo51w_MBUM6f3oH9Lvo-MeSbnzTRE"  # This should be stored in environment variables
                genai.configure(api_key=api_key)

                # For debugging - see what models are available
                print("Available models:")
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        print(m.name)

                # Create a simplified product list with only necessary fields
                simplified_products = []
                for p in products:
                    simplified_products.append({
                        "ProductId": p["ProductId"],
                        "Name": p["Name"],
                        "Description": p["Description"],
                        "Price": float(p["Price"]) if p["Price"] else 0,
                        "Stock": p["Stock"]
                    })

                # Use the model directly through GenerativeModel
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""
                You are a smart product recommendation assistant. A user searched for: "{user_input}".
                Based on this search query, find the 5 most relevant products from this list:
                
                {simplified_products}
                
                Return ONLY a JSON array of exactly 5 product objects with exactly these fields from the original data:
                ProductId, Name, Description, Price, Stock, image_path.
                
                Format your response as a valid JSON array that can be parsed with json.loads().
                """
                
                response = model.generate_content(prompt)
                
                # Extract the text from the response
                ai_output = response.text.strip()
                
                # Find JSON array in the response - sometimes the AI includes explanation text
                import re
                json_match = re.search(r'\[.*\]', ai_output, re.DOTALL)
                if json_match:
                    ai_output = json_match.group(0)
                
                print("AI OUTPUT:", ai_output)
                
                # Parse the JSON response
                top_products = json.loads(ai_output)
                
                # Ensure we have exactly 5 products, or take what we have
                if not isinstance(top_products, list):
                    top_products = []
                    flash("The AI couldn't find relevant products. Showing random selections instead.")
                    # Fall back to some products from our database
                    top_products = products[:5] if len(products) >= 5 else products
                
                return render_template('ai_search_results.html', products=top_products, query=user_input)

            except json.JSONDecodeError as je:
                print("JSON Decode Error:", str(je))
                print("AI Response:", ai_output if 'ai_output' in locals() else "No response")
                flash('AI response format error. Showing all products instead.')
                return render_template('ai_search_results.html', products=products[:5], query=user_input)
            
            except Exception as e:
                print("AI Search Error:", str(e))
                flash(f'Search error: {str(e)}. Showing all products.')
                return render_template('ai_search_results.html', products=products[:5], query=user_input)

        # GET request - show search form
        return render_template('ai_search.html')

    except Exception as e:
        flash(f'Error during AI search: {str(e)}')
        return redirect(url_for('buyer.dashboard'))

    finally:
        if conn:
            conn.close()