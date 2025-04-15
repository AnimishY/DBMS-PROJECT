import mysql.connector
from mysql.connector import Error
import sys

def connect_to_mysql():
    try:
        connection = mysql.connector.connect(
            host="LAPTOP-PLO5256K",
            user="admin",
            password="admin",
            database="virus",
            port=3306
        )
        if connection.is_connected():
            print("Connected to MySQL Server successfully!")
            db_info = connection.get_server_info()
            print(f"MySQL Server version: {db_info}")
            cursor = connection.cursor()
            cursor.execute("select database();")
            db_name = cursor.fetchone()[0]
            print(f"Connected to database: {db_name}")
            return connection
    except Error as e:
        print(f"Error Code: {e.errno}")
        print(f"SQLSTATE: {e.sqlstate}")
        print(f"Error Message: {str(e)}")
        if e.errno == 2003:
            print("Unable to connect to the database server. Please check if the server is running and the hostname is correct.")
        elif e.errno == 1045:
            print("Access denied. Please check username and password.")
        elif e.errno == 1049:
            print("Database does not exist.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        print(f"Error Type: {type(e).__name__}")
        return None