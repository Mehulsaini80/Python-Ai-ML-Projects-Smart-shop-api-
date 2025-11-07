import mysql.connector
from app import DB_CONFIG

def setup_database():
    try:
        # Connect to MySQL
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create users table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create products table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INT AUTO_INCREMENT PRIMARY KEY,
                platform VARCHAR(50) NOT NULL,
                sku VARCHAR(20) NOT NULL,
                product_name VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                discount_percent DECIMAL(5, 2) DEFAULT 0,
                discounted_price DECIMAL(10, 2),
                rating DECIMAL(3, 2) DEFAULT 4.0,
                stock INT DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create predictions table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                budget DECIMAL(10, 2) NOT NULL,
                platform VARCHAR(50),
                predicted_discount DECIMAL(5, 2) NOT NULL,
                predicted_platform VARCHAR(50) NOT NULL,
                discounted_price DECIMAL(10, 2) NOT NULL,
                savings DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("✅ Database tables created successfully!")
        
        # Verify tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("\nExisting tables:")
        for table in tables:
            print(f"- {table[0]}")
            
        # Count users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"\nCurrent users in database: {user_count}")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        print(f"❌ Database error: {err}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Setting up database tables...")
    setup_database()