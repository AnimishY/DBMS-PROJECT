from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config.database import connect_to_mysql
from functools import wraps
from utils.product_form import ProductForm  # Adjusted import path for relative import
from config.uploads import photos  # Import photos from the new module
import calendar
from datetime import datetime

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
    
    try:
        # Connect to database to fetch categories
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch all categories from database
        cursor.execute("SELECT CategoryId, Name FROM Category ORDER BY Name")
        categories = cursor.fetchall()
        
        if form.validate_on_submit():
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
        flash(f"Error: {str(e)}", 'danger')
        categories = []  # Default to empty list if database error
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('add_product.html', form=form, categories=categories)

@seller_blueprint.route('/add-product-confirmation', methods=['GET'])
@seller_login_required
def add_product_confirmation():
    return render_template('add_product_confirmation.html')

@seller_blueprint.route('/manage-products', methods=['GET'])
@seller_login_required
def manage_products():
    conn = None
    cursor = None
    low_stock_threshold = 5  # Default value
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch the seller's low stock threshold
        threshold_query = "SELECT LowStockThreshold FROM Seller WHERE SellerId = %s"
        cursor.execute(threshold_query, (session['seller_id'],))
        result = cursor.fetchone()
        if result:
            low_stock_threshold = result['LowStockThreshold']
        
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
    
    return render_template('manage_products.html', products=products, low_stock_threshold=low_stock_threshold)

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
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)

        # Fetch order history for the logged-in seller
        query = '''
        SELECT o.OrderId, o.OrderDate, o.TotalAmount, o.OrderStatus, 
               p.Name AS ProductName, oi.Quantity, b.BuyerId, 
               CONCAT(b.BuyerFirstName, ' ', b.BuyerLastName) AS BuyerName,
               s.ShipmentId, s.TrackingNumber, s.ShippingMethod
        FROM Orders o
        JOIN OrderItem oi ON o.OrderId = oi.OrderId
        JOIN Product p ON oi.ProductId = p.ProductId
        JOIN Buyer b ON o.BuyerId = b.BuyerId
        LEFT JOIN Shipment s ON o.OrderId = s.OrderId
        WHERE p.SellerId = %s
        ORDER BY o.OrderDate DESC
        '''
        cursor.execute(query, (session['seller_id'],))
        orders = cursor.fetchall()

        return render_template('view_orders.html', orders=orders)
    except Exception as e:
        flash(f"Failed to load orders: {str(e)}", 'danger')
        return redirect(url_for('seller.dashboard'))
    finally:
        if conn:
            conn.close()

@seller_blueprint.route('/update-order/<int:order_id>', methods=['GET', 'POST'])
@seller_login_required
def update_order(order_id):
    conn = None
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Update order status
            new_status = request.form['order_status']
            cursor.execute(
                "UPDATE Orders SET OrderStatus = %s WHERE OrderId = %s", 
                (new_status, order_id)
            )
            conn.commit()
            
            flash('Order status updated successfully!', 'success')
            
            # If status is "Shipped", redirect to shipment details page
            if new_status == 'Shipped':
                return redirect(url_for('seller.add_shipment', order_id=order_id))
                
            return redirect(url_for('seller.view_orders'))
            
        # GET request - show form with current order details
        cursor.execute(
            "SELECT OrderId, OrderStatus FROM Orders WHERE OrderId = %s", 
            (order_id,)
        )
        order = cursor.fetchone()
        
        if not order:
            flash('Order not found', 'danger')
            return redirect(url_for('seller.view_orders'))
            
        return render_template('update_order.html', order=order)
        
    except Exception as e:
        flash(f"Error updating order: {str(e)}", 'danger')
        return redirect(url_for('seller.view_orders'))
    finally:
        if conn:
            conn.close()

@seller_blueprint.route('/add-shipment/<int:order_id>', methods=['GET', 'POST'])
@seller_login_required
def add_shipment(order_id):
    conn = None
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)
        
        # Check if order exists and belongs to this seller
        check_query = '''
        SELECT o.OrderId, o.OrderStatus 
        FROM Orders o
        JOIN OrderItem oi ON o.OrderId = oi.OrderId
        JOIN Product p ON oi.ProductId = p.ProductId
        WHERE o.OrderId = %s AND p.SellerId = %s
        LIMIT 1
        '''
        cursor.execute(check_query, (order_id, session['seller_id']))
        order = cursor.fetchone()
        
        if not order:
            flash('Order not found or unauthorized access', 'danger')
            return redirect(url_for('seller.view_orders'))
        
        # Check if shipment already exists
        cursor.execute("SELECT * FROM Shipment WHERE OrderId = %s", (order_id,))
        existing_shipment = cursor.fetchone()
        
        if request.method == 'POST':
            # If shipment exists, update it
            shipping_method = request.form['shipping_method']
            tracking_number = request.form['tracking_number']
            shipment_date = request.form['shipment_date']
            delivery_date = request.form.get('delivery_date') # Optional
            
            if existing_shipment:
                update_query = '''
                UPDATE Shipment 
                SET ShippingMethod = %s, TrackingNumber = %s, 
                    ShipmentDate = %s, DeliveryDate = %s
                WHERE OrderId = %s
                '''
                cursor.execute(update_query, 
                              (shipping_method, tracking_number, 
                               shipment_date, delivery_date, order_id))
                flash('Shipment updated successfully!', 'success')
            else:
                # Create new shipment record
                insert_query = '''
                INSERT INTO Shipment (OrderId, ShipmentDate, DeliveryDate, 
                                     ShippingMethod, TrackingNumber)
                VALUES (%s, %s, %s, %s, %s)
                '''
                cursor.execute(insert_query, 
                              (order_id, shipment_date, delivery_date, 
                               shipping_method, tracking_number))
                
                # Update order status if not already shipped
                if order['OrderStatus'] != 'Shipped':
                    cursor.execute("UPDATE Orders SET OrderStatus = 'Shipped' WHERE OrderId = %s", 
                                  (order_id,))
                    
                flash('Shipment details added successfully!', 'success')
                
            conn.commit()
            return redirect(url_for('seller.view_orders'))
        
        # For GET request, show the form with existing data if available
        return render_template('add_shipment.html', 
                               order_id=order_id, 
                               shipment=existing_shipment)
        
    except Exception as e:
        flash(f"Error managing shipment: {str(e)}", 'danger')
        return redirect(url_for('seller.view_orders'))
    finally:
        if conn:
            conn.close()

@seller_blueprint.route('/view-shipment/<int:order_id>')
@seller_login_required
def view_shipment(order_id):
    conn = None
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)
        
        # Get shipment details
        query = '''
        SELECT s.*, o.OrderStatus 
        FROM Shipment s
        JOIN Orders o ON s.OrderId = o.OrderId
        WHERE s.OrderId = %s
        '''
        cursor.execute(query, (order_id,))
        shipment = cursor.fetchone()
        
        if not shipment:
            flash('No shipment details found for this order', 'warning')
            return redirect(url_for('seller.view_orders'))
            
        return render_template('view_shipment.html', shipment=shipment)
        
    except Exception as e:
        flash(f"Error viewing shipment: {str(e)}", 'danger')
        return redirect(url_for('seller.view_orders'))
    finally:
        if conn:
            conn.close()

@seller_blueprint.route('/buyer-details/<int:buyer_id>', methods=['GET'])
@seller_login_required
def buyer_details(buyer_id):
    conn = None
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)

        # Fetch buyer details
        query = '''
        SELECT BuyerFirstName, BuyerLastName, Email, AddressLine1, AddressLine2, 
               City, States, PinCode
        FROM Buyer
        WHERE BuyerId = %s
        '''
        cursor.execute(query, (buyer_id,))
        buyer = cursor.fetchone()

        if not buyer:
            flash('Buyer details not found.', 'danger')
            return redirect(url_for('seller.view_orders'))

        return render_template('buyer_details.html', buyer=buyer)
    except Exception as e:
        flash(f"Failed to load buyer details: {str(e)}", 'danger')
        return redirect(url_for('seller.view_orders'))
    finally:
        if conn:
            conn.close()

@seller_blueprint.route('/product-history', methods=['GET'])
@seller_login_required
def product_history():
    conn = None
    cursor = None
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch product history for the logged-in seller
        query = """
        SELECT ProductId, Name, Description, Price, Stock, CreatedAt
        FROM Product
        WHERE SellerId = %s
        ORDER BY CreatedAt DESC
        """
        cursor.execute(query, (session['seller_id'],))
        products = cursor.fetchall()
    except Exception as e:
        flash(f"Error fetching product history: {str(e)}", 'danger')
        products = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('seller_product_history.html', products=products)

@seller_blueprint.route('/analytics', methods=['GET'])
@seller_login_required
def analytics():
    conn = None
    cursor = None
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor(dictionary=True)
        seller_id = session['seller_id']
        
        # Get total revenue
        total_revenue_query = '''
        SELECT COALESCE(SUM(oi.Quantity * oi.UnitPrice), 0) as TotalRevenue
        FROM OrderItem oi
        JOIN Product p ON oi.ProductId = p.ProductId
        WHERE p.SellerId = %s
        '''
        cursor.execute(total_revenue_query, (seller_id,))
        total_revenue = cursor.fetchone()['TotalRevenue']
        
        # Get monthly revenue for the current year
        current_year = datetime.now().year
        monthly_revenue_query = '''
        SELECT 
            MONTH(o.OrderDate) as Month,
            COALESCE(SUM(oi.Quantity * oi.UnitPrice), 0) as Revenue
        FROM OrderItem oi
        JOIN Orders o ON oi.OrderId = o.OrderId
        JOIN Product p ON oi.ProductId = p.ProductId
        WHERE p.SellerId = %s AND YEAR(o.OrderDate) = %s
        GROUP BY MONTH(o.OrderDate)
        ORDER BY MONTH(o.OrderDate)
        '''
        cursor.execute(monthly_revenue_query, (seller_id, current_year))
        monthly_data = cursor.fetchall()
        
        # Format monthly data for display
        months = [calendar.month_name[month['Month']] for month in monthly_data]
        monthly_revenue = [float(month['Revenue']) for month in monthly_data]
        
        # Get category-wise revenue
        category_revenue_query = '''
        SELECT 
            c.Name as CategoryName,
            COALESCE(SUM(oi.Quantity * oi.UnitPrice), 0) as Revenue
        FROM OrderItem oi
        JOIN Product p ON oi.ProductId = p.ProductId
        JOIN Category c ON p.CategoryId = c.CategoryId
        WHERE p.SellerId = %s
        GROUP BY c.CategoryId
        ORDER BY Revenue DESC
        '''
        cursor.execute(category_revenue_query, (seller_id,))
        category_data = cursor.fetchall()
        
        # Get top 5 selling products
        top_products_query = '''
        SELECT 
            p.ProductId,
            p.Name,
            p.image_path,
            COALESCE(SUM(oi.Quantity), 0) as TotalQuantitySold,
            COALESCE(SUM(oi.Quantity * oi.UnitPrice), 0) as TotalRevenue
        FROM OrderItem oi
        JOIN Product p ON oi.ProductId = p.ProductId
        WHERE p.SellerId = %s
        GROUP BY p.ProductId
        ORDER BY TotalQuantitySold DESC
        LIMIT 5
        '''
        cursor.execute(top_products_query, (seller_id,))
        top_products = cursor.fetchall()
        
        return render_template(
            'seller_analytics.html', 
            total_revenue=total_revenue,
            months=months,
            monthly_revenue=monthly_revenue,
            category_data=category_data,
            top_products=top_products,
            store_name=session.get('store_name')
        )
        
    except Exception as e:
        flash(f"Error fetching analytics data: {str(e)}", 'danger')
        return redirect(url_for('seller.dashboard'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@seller_blueprint.route('/update-low-stock-threshold', methods=['POST'])
@seller_login_required
def update_low_stock_threshold():
    new_threshold = request.form.get('low_stock_threshold')
    conn = None
    cursor = None
    try:
        conn = connect_to_mysql()
        cursor = conn.cursor()
        
        # Update the seller's low stock threshold
        query = "UPDATE Seller SET LowStockThreshold = %s WHERE SellerId = %s"
        cursor.execute(query, (new_threshold, session['seller_id']))
        conn.commit()
        
        flash('Low stock threshold updated successfully!', 'success')
    except Exception as e:
        flash(f"Error updating low stock threshold: {str(e)}", 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('seller.manage_products'))

