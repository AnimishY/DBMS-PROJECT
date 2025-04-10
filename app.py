from flask import Flask, redirect, url_for, render_template, session
from flask_uploads import configure_uploads
from config.schema import init_db
from config.uploads import photos  # Import photos from the new module
from routes.buyer_routes import buyer_blueprint
from routes.seller_routes import seller_blueprint

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure secret key

# Configure upload folder
app.config['UPLOADED_PHOTOS_DEST'] = 'static/uploads'  # Folder to store images

# Set up Flask-Uploads
configure_uploads(app, photos)

# Initialize database schema
with app.app_context():
    init_db()

# Register blueprints
app.register_blueprint(seller_blueprint, url_prefix='/seller')
app.register_blueprint(buyer_blueprint, url_prefix='/buyer')

@app.route('/')
def home():
    return render_template('landing_page.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

if __name__ == "__main__":
    app.run(debug=True)
