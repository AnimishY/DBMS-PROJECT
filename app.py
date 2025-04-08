from flask import Flask, request, render_template, redirect, url_for, session
import mysql.connector
from mysql.connector import Error
import json
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def connect_to_mysql():
    try:
        connection = mysql.connector.connect(
            host="animish",
            user="admin",
            password="admin",
            database="virus",
            port=3306
        )
        return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

def load_users():
    try:
        with open('users.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open('users.json', 'w') as file:
        json.dump(users, file)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users:
            return "User already exists!"
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        users[username] = hashed_password.decode('utf-8')
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and bcrypt.checkpw(password.encode('utf-8'), users[username].encode('utf-8')):
            session['username'] = username
            return redirect(url_for('index'))
        return "Invalid credentials!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/buyer', methods=['POST'])
def get_buyer():
    if 'username' not in session:
        return redirect(url_for('login'))
    buyer_id = request.form['buyerId']
    connection = connect_to_mysql()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM buyer WHERE buyerId = %s", (buyer_id,))
            buyer = cursor.fetchone()
            return render_template('buyer.html', buyer=buyer)
        except Error as e:
            return f"Error while fetching data: {e}"
        finally:
            connection.close()
    return "Failed to connect to the database."

if __name__ == "__main__":
    app.run(debug=True)
