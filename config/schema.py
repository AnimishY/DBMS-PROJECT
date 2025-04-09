from config.database import connect_to_mysql

def init_db():
    conn = connect_to_mysql()
    if not conn:
        print("Failed to connect to database")
        return False

    cursor = conn.cursor()
    
    try:
        # Create Buyer table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buyer (
                BuyerId INT AUTO_INCREMENT PRIMARY KEY,
                BuyerFirstName VARCHAR(50) NOT NULL,
                BuyerLastName VARCHAR(50) NOT NULL,
                Email VARCHAR(100) UNIQUE NOT NULL,
                PasswordHash VARCHAR(255) NOT NULL,
                AddressLine1 VARCHAR(100) NOT NULL,
                AddressLine2 VARCHAR(100),
                City VARCHAR(50) NOT NULL,
                States VARCHAR(50) NOT NULL,
                PinCode VARCHAR(10) NOT NULL,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create Seller table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seller (
                SellerId INT AUTO_INCREMENT PRIMARY KEY,
                StoreName VARCHAR(100) NOT NULL,
                Contact VARCHAR(15) NOT NULL,
                Email VARCHAR(100) UNIQUE NOT NULL,
                PasswordHash VARCHAR(255) NOT NULL,
                AddressLine1 VARCHAR(100) NOT NULL,
                AddressLine2 VARCHAR(100),
                City VARCHAR(50) NOT NULL,
                States VARCHAR(50) NOT NULL,
                PinCode VARCHAR(10) NOT NULL,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        print("Database schema initialized successfully")
        return True
        
    except Exception as e:
        print(f"Error initializing database schema: {str(e)}")
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()