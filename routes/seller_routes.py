from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config.database import connect_to_mysql
from functools import wraps
from utils.product_form import ProductForm  # Adjusted import path for relative import
from config.uploads import photos  # Import photos from the new module

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

@seller_blueprint.route('/products', methods=['GET'])
@seller_login_required
def list_products():
    conn = connect_to_mysql()
    cursor = conn.cursor(dictionary=True)  # Use dictionary=True to get results as dictionaries
    
    try:
        # Fetch products for the logged-in seller
        query = "SELECT * FROM Product WHERE SellerId = %s"
        cursor.execute(query, (session['seller_id'],))  # Assuming seller_id is stored in session
        products = cursor.fetchall()  # Fetch all products
    except Exception as e:
        products = []  # Default to an empty list if there's an error
        flash(f"Error fetching products: {str(e)}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    # Pass the products to the template
    return render_template('product_list.html', products=products)

@seller_blueprint.route('/add-product', methods=['GET', 'POST'])
def add_product():
    form = ProductForm()
    conn = None
    cursor = None  # Initialize cursor to None
    if form.validate_on_submit():
        try:
            conn = connect_to_mysql()
            if not conn:
                flash('Database connection failed')
                return redirect(url_for('seller.add_product'))

            cursor = conn.cursor(dictionary=True, buffered=True)

            # Save the uploaded image
            image_filename = None
            if form.image.data:
                raw_filename = form.image.data.filename
                image_filename = secure_filename(raw_filename)
                photos.save(form.image.data, name=image_filename)

            # Save product details to the database
            name = form.name.data
            description = form.description.data
            price = form.price.data
            stock = form.stock.data
            category_id = request.form.get('category_id')
            seller_id = session['seller_id']

            query = """
            INSERT INTO Product (Name, Description, Price, Stock, SellerId, CategoryId, image_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (name, description, price, stock, seller_id, category_id, image_filename)
            cursor.execute(query, values)
            conn.commit()

            # Redirect to confirmation page
            return redirect(url_for('seller.add_product_confirmation'))

        except Exception as e:
            flash(f"Error adding product: {str(e)}", 'danger')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('add_product.html', form=form)

@seller_blueprint.route('/add-product-confirmation', methods=['GET'])
@seller_login_required
def add_product_confirmation():
    return render_template('add_product_confirmation.html')

@seller_blueprint.route('/manage-products', methods=['GET'])
@seller_login_required
def manage_products():
    conn = None
    cursor = None
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch products for the logged-in seller
        query = """
        SELECT ProductId, Name, Description, Price, Stock, CategoryId, image_path
        FROM Product
        WHERE SellerId = %s
        """
        cursor.execute(query, (session['seller_id'],))
        products = cursor.fetchall()
    except Exception as e:
        flash(f"Error fetching products: {str(e)}", 'danger')
        products = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('manage_products.html', products=products)

@seller_blueprint.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
@seller_login_required
def edit_product(product_id):
    form = ProductForm()
    conn = None
    cursor = None
    if request.method == 'POST' and form.validate_on_submit():
        try:
            conn = connect_to_mysql()
            cursor = conn.cursor(dictionary=True)
            
            # Update product details in the database
            query = """
            UPDATE Product
            SET Name = %s, Description = %s, Price = %s, Stock = %s
            WHERE ProductId = %s AND SellerId = %s
            """
            values = (form.name.data, form.description.data, form.price.data, form.stock.data, product_id, session['seller_id'])
            cursor.execute(query, values)
            conn.commit()
            
            flash('Product updated successfully!', 'success')
            return redirect(url_for('seller.manage_products'))
        except Exception as e:
            flash(f"Error updating product: {str(e)}", 'danger')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    else:
        try:
            conn = connect_to_mysql()
            cursor = conn.cursor(dictionary=True)
            
            # Fetch product details to pre-fill the form
            query = "SELECT * FROM Product WHERE ProductId = %s AND SellerId = %s"
            cursor.execute(query, (product_id, session['seller_id']))
            product = cursor.fetchone()
            if product:
                form.name.data = product['Name']
                form.description.data = product['Description']
                form.price.data = product['Price']
                form.stock.data = product['Stock']
            else:
                flash('Product not found or unauthorized access.', 'danger')
                return redirect(url_for('seller.manage_products'))
        except Exception as e:
            flash(f"Error fetching product: {str(e)}", 'danger')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    return render_template('edit_product.html', form=form)

@seller_blueprint.route('/delete-product/<int:product_id>', methods=['POST'])
@seller_login_required
def delete_product(product_id):
    conn = None
    cursor = None
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)
        
        # Delete the product from the database
        query = "DELETE FROM Product WHERE ProductId = %s AND SellerId = %s"
        cursor.execute(query, (product_id, session['seller_id']))
        conn.commit()
        
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        flash(f"Error deleting product: {str(e)}", 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('seller.manage_products'))

@seller_blueprint.route('/view-orders', methods=['GET'])
@seller_login_required
def view_orders():
    conn = None
    cursor = None
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch products for the logged-in seller, including image_path
        query = """
        SELECT ProductId, Name, Description, Price, Stock, CategoryId, image_path
        FROM Product
        WHERE SellerId = %s
        """
        cursor.execute(query, (session['seller_id'],))
        products = cursor.fetchall()
    except Exception as e:
        flash(f"Error fetching products: {str(e)}", 'danger')
        products = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('view_orders.html', products=products)