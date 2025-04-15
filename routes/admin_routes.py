from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from functools import wraps
# Ensure database connection is imported
from config.database import connect_to_mysql
from datetime import datetime

admin_blueprint = Blueprint('admin', __name__)


def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login as admin first')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Hardcoded admin credentials
        if username == 'admin' and password == 'admin':
            session['admin_id'] = 'admin'
            session['admin_name'] = 'Administrator'
            flash('Admin login successful!')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid admin credentials')
            return redirect(url_for('admin.login'))

    return render_template('admin_login.html')


@admin_blueprint.route('/dashboard')
@admin_login_required
def dashboard():
    return render_template('admin_dashboard.html', admin_name=session.get('admin_name'))


@admin_blueprint.route('/logout')
def logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    flash('Admin logged out successfully')
    return redirect(url_for('home'))


@admin_blueprint.route('/analytics', methods=['GET'])
@admin_login_required
def analytics():
    # Default report is 'active_buyers'
    report = request.args.get('report', 'active_buyers')
    active_buyers = []
    top_products = []
    top_sellers = []
    buyers = []  # Add this variable to store buyers without orders

    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed', 'danger')
            return redirect(url_for('admin.dashboard'))

        cursor = conn.cursor(dictionary=True)

        if report == 'active_buyers':
            query = '''
                SELECT b.BuyerId AS user_id, 
                       CONCAT(b.BuyerFirstName, ' ', b.BuyerLastName) AS name, 
                       b.Email AS email, 
                       COUNT(o.OrderId) AS order_count, 
                       SUM(o.TotalAmount) AS total_spent
                FROM Buyer b
                JOIN Orders o ON b.BuyerId = o.BuyerId
                GROUP BY b.BuyerId
                ORDER BY order_count DESC, total_spent DESC
                LIMIT 5
            '''
            cursor.execute(query)
            active_buyers = cursor.fetchall()

        elif report == 'top_products':
            query = '''
                SELECT p.ProductId, p.Name AS product_name, 
                       SUM(oi.Quantity) AS total_quantity_sold
                FROM Product p
                JOIN OrderItem oi ON p.ProductId = oi.ProductId
                GROUP BY p.ProductId
                ORDER BY total_quantity_sold DESC
                LIMIT 5
            '''
            cursor.execute(query)
            top_products = cursor.fetchall()

        elif report == 'top_sellers':
            query = '''
                SELECT s.SellerId, s.StoreName, 
                       SUM(o.TotalAmount) AS total_revenue
                FROM Seller s
                JOIN Product p ON s.SellerId = p.SellerId
                JOIN OrderItem oi ON p.ProductId = oi.ProductId
                JOIN Orders o ON oi.OrderId = o.OrderId
                GROUP BY s.SellerId
                ORDER BY total_revenue DESC
                LIMIT 5
            '''
            cursor.execute(query)
            top_sellers = cursor.fetchall()

        elif report == 'buyers_without_orders':
            query = '''
                SELECT 
                b.BuyerId,
                CONCAT(b.BuyerFirstName, ' ', b.BuyerLastName) AS name,
                b.Email AS email
                FROM Buyer b
                LEFT JOIN Orders o ON b.BuyerId = o.BuyerId
                WHERE o.BuyerId IS NULL
                ORDER BY name ASC
            '''
            cursor.execute(query)
            buyers = cursor.fetchall()

    except Exception as e:
        flash(f"Failed to generate analytics report: {str(e)}", 'danger')
    finally:
        if conn:
            conn.close()

    return render_template(
        'admin_analytics.html',
        active_buyers=active_buyers,
        top_products=top_products,
        top_sellers=top_sellers,
        buyers=buyers,  # Add the buyers variable to the template context
        report=report
    )


@admin_blueprint.route('/buyer-orders/<int:buyer_id>', methods=['GET'])
@admin_login_required
def get_buyer_orders(buyer_id):
    orders = []
    buyer_details = None
    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed', 'danger')
            return redirect(url_for('admin.dashboard'))

        cursor = conn.cursor(dictionary=True)

        # Fetch buyer details
        buyer_query = '''
            SELECT BuyerFirstName, BuyerLastName, Email, AddressLine1, AddressLine2, 
                   City, States, PinCode
            FROM Buyer
            WHERE BuyerId = %s
        '''
        cursor.execute(buyer_query, (buyer_id,))
        buyer_details = cursor.fetchone()

        if not buyer_details:
            flash('Buyer not found', 'danger')
            return redirect(url_for('admin.dashboard'))

        # Fetch orders for the buyer
        orders_query = '''
            SELECT o.OrderId, o.OrderDate, o.TotalAmount, o.OrderStatus
            FROM Orders o
            WHERE o.BuyerId = %s
            ORDER BY o.OrderDate DESC
        '''
        cursor.execute(orders_query, (buyer_id,))
        orders = cursor.fetchall()
    except Exception as e:
        flash(f"Failed to fetch orders for buyer: {str(e)}", 'danger')
    finally:
        if conn:
            conn.close()

    return render_template('admin_buyer_orders.html', orders=orders, buyer_id=buyer_id, buyer_details=buyer_details)


@admin_blueprint.route('/buyer-orders-input', methods=['GET', 'POST'])
@admin_login_required
def buyer_orders_input():
    if request.method == 'POST':
        buyer_id = request.form.get('buyer_id')
        if buyer_id:
            return redirect(url_for('admin.get_buyer_orders', buyer_id=buyer_id))
        flash('Please enter a valid Buyer ID', 'danger')
    return render_template('admin_buyer_orders_input.html')


@admin_blueprint.route('/seller-sales-report', methods=['GET'])
@admin_login_required
def seller_sales_report():
    report = []
    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed', 'danger')
            return redirect(url_for('admin.dashboard'))

        cursor = conn.cursor(dictionary=True)
        query = '''
            SELECT p.ProductId, p.Name AS product_name, p.Stock AS current_stock, 
                   COALESCE(SUM(oi.Quantity), 0) AS total_quantity_sold
            FROM Product p
            LEFT JOIN OrderItem oi ON p.ProductId = oi.ProductId
            GROUP BY p.ProductId
            ORDER BY total_quantity_sold DESC
        '''
        cursor.execute(query)
        report = cursor.fetchall()
    except Exception as e:
        flash(f"Failed to generate seller sales report: {str(e)}", 'danger')
    finally:
        if conn:
            conn.close()

    return render_template('admin_seller_sales_report.html', report=report)


@admin_blueprint.route('/total-revenue', methods=['GET'])
@admin_login_required
def total_revenue():
    revenue = 0
    month_wise_revenue = []
    category_wise_revenue = []
    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed', 'danger')
            return redirect(url_for('admin.dashboard'))

        cursor = conn.cursor()

        # Total revenue
        query = 'SELECT SUM(TotalAmount) FROM Orders'
        cursor.execute(query)
        result = cursor.fetchone()
        revenue = result[0] if result[0] else 0

        # Month-wise revenue
        month_query = '''
            SELECT DATE_FORMAT(OrderDate, '%Y-%m') AS month, SUM(TotalAmount) AS total
            FROM Orders
            GROUP BY month
            ORDER BY month DESC
        '''
        cursor.execute(month_query)
        month_wise_revenue = cursor.fetchall()

        # Category-wise revenue
        category_query = '''
            SELECT c.Name AS category, SUM(oi.Quantity * oi.UnitPrice) AS total
            FROM OrderItem oi
            JOIN Product p ON oi.ProductId = p.ProductId
            JOIN Category c ON p.CategoryId = c.CategoryId
            GROUP BY c.CategoryId
            ORDER BY total DESC
        '''
        cursor.execute(category_query)
        category_wise_revenue = cursor.fetchall()

    except Exception as e:
        flash(f"Failed to calculate total revenue: {str(e)}", 'danger')
    finally:
        if conn:
            conn.close()

    return render_template(
        'admin_total_revenue.html',
        revenue=revenue,
        month_wise_revenue=month_wise_revenue,
        category_wise_revenue=category_wise_revenue
    )


@admin_blueprint.route('/view_users', methods=['GET'])
@admin_login_required
def view_users():
    users = []
    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed', 'danger')
            return redirect(url_for('admin.dashboard'))

        cursor = conn.cursor(dictionary=True)
        query = '''
            SELECT BuyerId AS user_id, 
                   CONCAT(BuyerFirstName, ' ', BuyerLastName) AS name, 
                   Email AS email
            FROM Buyer
            ORDER BY BuyerFirstName ASC
        '''
        cursor.execute(query)
        users = cursor.fetchall()
    except Exception as e:
        flash(f"Failed to fetch users: {str(e)}", 'danger')
    finally:
        if conn:
            conn.close()

    return render_template('admin_view_users.html', users=users)


@admin_blueprint.route('/seller-sales-input', methods=['GET', 'POST'])
@admin_login_required
def seller_sales_input():
    if request.method == 'POST':
        seller_id = request.form.get('seller_id')
        if seller_id:
            return redirect(url_for('admin.get_seller_sales', seller_id=seller_id))
        flash('Please enter a valid Seller ID', 'danger')
    return render_template('admin_seller_sales_input.html')


@admin_blueprint.route('/seller-sales/<int:seller_id>', methods=['GET'])
@admin_login_required
def get_seller_sales(seller_id):
    seller_details = None
    sales_stats = []
    conn = None
    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed', 'danger')
            return redirect(url_for('admin.dashboard'))

        cursor = conn.cursor(dictionary=True)

        # Fetch seller details
        seller_query = '''
            SELECT SellerId, StoreName, SellerContact, Email, 
                   StoreAddressLine1, StoreAddressLine2, City, States, PinCode
            FROM Seller
            WHERE SellerId = %s
        '''
        cursor.execute(seller_query, (seller_id,))
        seller_details = cursor.fetchone()

        if not seller_details:
            flash('Seller not found', 'danger')
            return redirect(url_for('admin.dashboard'))

        # Fetch all products and their sold quantities for the seller
        sales_query = '''
            SELECT p.ProductId, p.Name AS product_name, p.Stock AS current_stock, 
                   COALESCE(SUM(oi.Quantity), 0) AS total_quantity_sold
            FROM Product p
            LEFT JOIN OrderItem oi ON p.ProductId = oi.ProductId
            WHERE p.SellerId = %s
            GROUP BY p.ProductId
            ORDER BY total_quantity_sold DESC
        '''
        cursor.execute(sales_query, (seller_id,))
        sales_stats = cursor.fetchall()

        # Calculate total revenue for the seller
        revenue_query = '''
            SELECT COALESCE(SUM(o.TotalAmount), 0) AS total_revenue
            FROM Orders o
            JOIN OrderItem oi ON o.OrderId = oi.OrderId
            JOIN Product p ON oi.ProductId = p.ProductId
            WHERE p.SellerId = %s
        '''
        cursor.execute(revenue_query, (seller_id,))
        revenue_result = cursor.fetchone()
        seller_details['total_revenue'] = revenue_result['total_revenue'] if revenue_result else 0

    except Exception as e:
        flash(f"Failed to fetch sales data for seller: {str(e)}", 'danger')
    finally:
        if conn:
            conn.close()

    return render_template('admin_seller_sales_report.html', seller_details=seller_details, sales_stats=sales_stats)


@admin_blueprint.route('/buyers-without-orders', methods=['GET'])
@admin_login_required
def buyers_without_orders():
    buyers = []
    conn = None
    sort_by = request.args.get('sort', 'name')  # Default sort by name

    try:
        conn = connect_to_mysql()
        if not conn:
            flash('Database connection failed', 'danger')
            return redirect(url_for('admin.dashboard'))

        cursor = conn.cursor(dictionary=True)

        # Enhanced query with buyer details
        query = '''
            SELECT 
    b.BuyerId,
    CONCAT(b.BuyerFirstName, ' ', b.BuyerLastName) AS name,
    b.Email AS email,
    b.City,
    b.States
FROM Buyer b
LEFT JOIN Orders o ON b.BuyerId = o.BuyerId
WHERE o.BuyerId IS NULL;
        '''

        cursor.execute(query)
        buyers = cursor.fetchall()

    except Exception as e:
        flash(f"Failed to fetch buyers without orders: {str(e)}", 'danger')
        return redirect(url_for('admin.dashboard'))

    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    return render_template('admin_buyers_without_orders.html',
                           buyers=buyers,
                           total_inactive=len(buyers))
