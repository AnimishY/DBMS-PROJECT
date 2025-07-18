from flask import Flask, redirect, url_for, render_template, session
from config.schema import init_db
from routes.buyer_routes import buyer_blueprint
from routes.seller_routes import seller_blueprint
from routes.admin_routes import admin_blueprint
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key

# Set upload folder path
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize database schema
with app.app_context():
    init_db()

# Register blueprints
app.register_blueprint(seller_blueprint, url_prefix='/seller')
app.register_blueprint(buyer_blueprint, url_prefix='/buyer')
app.register_blueprint(admin_blueprint, url_prefix='/admin')

# Routes
@app.route('/')
def home():
    return render_template('landing_page.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

# Run the app (Fly.io compatible)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
