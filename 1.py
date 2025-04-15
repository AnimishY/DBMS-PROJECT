import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash

def connect_to_mysql():
    try:
        connection = mysql.connector.connect(
            host="animish",
            user="admin",
            password="admin",
            database="virus",  # Specify the database name
            port=3306
        )
        if connection.is_connected():
            print("Connected to MySQL Server successfully!")
            return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

def fetch_buyer_table(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM buyer LIMIT 5")  # Query to fetch all rows from the 'buyer' table
        rows = cursor.fetchall()
        print("Buyer Table:")
        for row in rows:
            print(row)
    except Error as e:
        print(f"Error while fetching data: {e}")

def update_buyer_passwords(connection):
    try:
        cursor = connection.cursor()
        # Get all buyer IDs
        cursor.execute("SELECT BuyerId FROM buyer")
        buyer_ids = cursor.fetchall()
        
        # Generate hashed password for '111'
        hashed_password = generate_password_hash('111')
        
        # Update each buyer's password
        update_query = "UPDATE buyer SET PasswordHash = %s WHERE BuyerId = %s"
        for buyer_id in buyer_ids:
            cursor.execute(update_query, (hashed_password, buyer_id[0]))
        
        connection.commit()
        print(f"Updated passwords for {len(buyer_ids)} buyers")
    except Error as e:
        print(f"Error while updating buyer passwords: {e}")

def update_seller_passwords(connection):
    try:
        cursor = connection.cursor()
        # Get all seller IDs
        cursor.execute("SELECT SellerId FROM seller")
        seller_ids = cursor.fetchall()
        
        # Generate hashed password for '111'
        hashed_password = generate_password_hash('111')
        
        # Update each seller's password
        update_query = "UPDATE seller SET PasswordHash = %s WHERE SellerId = %s"
        for seller_id in seller_ids:
            cursor.execute(update_query, (hashed_password, seller_id[0]))
        
        connection.commit()
        print(f"Updated passwords for {len(seller_ids)} sellers")
    except Error as e:
        print(f"Error while updating seller passwords: {e}")

if __name__ == "__main__":
    connection = connect_to_mysql()
    if connection:
        fetch_buyer_table(connection)
        # Update passwords in both tables
        update_buyer_passwords(connection)
        update_seller_passwords(connection)
        connection.close()
        print("Password update completed successfully.")
