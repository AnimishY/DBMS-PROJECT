import mysql.connector
from mysql.connector import Error

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

if __name__ == "__main__":
    connection = connect_to_mysql()
    if connection:
        fetch_buyer_table(connection)
        connection.close()
