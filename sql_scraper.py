"""
Complete Product Scraper - Name, Price, Rating, Reviews, Image
==============================================================
Extracts: Product Name, Price, Rating, Review Count, Image URL
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import mysql.connector
from mysql.connector import Error
import time
import json
from datetime import datetime
import re

# ============================================
# MySQL DATABASE HANDLER
# ============================================

class ProductDatabase:
    def __init__(self, host, user, password, database):
        self.config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'Mehulmysql@90',
            'database': 'project_smart' 
        } 
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to MySQL database"""
        try:
            self.conn = mysql.connector.connect(**self.config)
            if self.conn.is_connected():
                self.cursor = self.conn.cursor()
                print(f"✓ Connected to MySQL: {self.config['database']}")
                return True
        except Error as e:
            print(f"✗ Connection Error: {e}")
            return False
    
    def setup_table(self):
        """Create or verify table structure"""
        try:
            # Check if table exists
            self.cursor.execute("SHOW TABLES LIKE 'products_data'")
            table_exists = self.cursor.fetchone()
            
            if not table_exists:
                print("Creating products_data table...")
                self.cursor.execute('''
                    CREATE TABLE products_data (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        product_name VARCHAR(500),
                        price VARCHAR(100),
                        rating VARCHAR(50),
                        review_count VARCHAR(50),
                        image_url TEXT,
                        url TEXT,
                        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        additional_data JSON
                    )
                ''')
                self.conn.commit()
                print("✓ Table created successfully")
            else:
                # Check if image_url column exists
                self.cursor.execute("DESCRIBE products_data")
                columns = [col[0] for col in self.cursor.fetchall()]
                
                if 'image_url' not in columns:
                    print("Adding image_url column...")
                    self.cursor.execute("ALTER TABLE products_data ADD COLUMN image_url TEXT AFTER rating")
                    self.conn.commit()
                
                if 'review_count' not in columns:
                    print("Adding review_count column...")
                    self.cursor.execute("ALTER TABLE products_data ADD COLUMN review_count VARCHAR(50) AFTER rating")
                    self.conn.commit()
                
                if 'product_name' not in columns and 'title' in columns:
                    print("Renaming title to product_name...")
                    self.cursor.execute("ALTER TABLE products_data CHANGE title product_name VARCHAR(500)")
                    self.conn.commit()
                
                print("✓ Table structure verified")
            
            return True
            
        except Error as e:
            print(f"✗ Table setup error: {e}")
            return False
    
    def insert_product(self, product_data):
        """Insert product into database"""
        try:
            query = '''
                INSERT INTO products_data 
                (product_name, price, rating, review_count, image_url, url, scraped_at, additional_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            '''
            
            values = (
                product_data.get('product_name', 'N/A'),
                product_data.get('price', 'N/A'),
                product_data.get('rating', 'N/A'),
                product_data.get('review_count', 'N/A'),
                product_data.get('image_url', 'N/A'),
                product_data.get('url', 'N/A'),
                datetime.now(),
                json.dumps(product_data)
            )
            
            self.cursor.execute(query, values)
            self.conn.commit()
            
            inserted_id = self.cursor.lastrowid
            print(f"\n✅ Saved to database (ID: {inserted_id})")
            
            return inserted_id
            
        except Error as e:
            print(f"✗ Insert error: {e}")
            self.conn.rollback()
            return None
    
    def get_all_products(self):
        """Get all products"""
        try:
            self.cursor.execute('SELECT * FROM products_data ORDER BY scraped_at DESC')
            return self.cursor.fetchall()
        except Error as e:
            print(f"✗ Error: {e}")
            return []
    
    def display_products(self):
        """Display products in table format"""
        products = self.get_all_products()
        
        if not products:
            print("\n⚠ No products found")
            return
        
        print("\n" + "="*130)
        print(f"{'ID':<4} {'Product Name':<45} {'Price':<12} {'Rating':<8} {'Reviews':<10} {'Image':<8}")
        print("="*130)
        
        for p in products:
            product_name = str(p[1])[:45] if p[1] else 'N/A'
            price = str(p[2])[:12] if p[2] else 'N/A'
            rating = str(p[3])[:8] if p[3] else 'N/A'
            reviews = str(p[4])[:10] if p[4] else 'N/A'
            has_image = '✓' if p[5] and p[5] != 'N/A' else '✗'
            
            print(f"{p[0]:<4} {product_name:<45} {price:<12} {rating:<8} {reviews:<10} {has_image:<8}")
        
        print("="*130)
        print(f"Total: {len(products)} products")
    
    def export_to_csv(self, filename='products_export.csv'):
        """Export products to CSV"""
        try:
            import pandas as pd
            
            products = self.get_all_products()
            if not products:
                print("No products to export")
                return
            
            df = pd.DataFrame(products, columns=[
                'id', 'product_name', 'price', 'rating', 'review_count', 
                'image_url', 'url', 'scraped_at', 'additional_data'
            ])
            
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"✓ Exported to {filename}")
            
        except Exception as e:
            print(f"✗ Export error: {e}")
    
    def close(self):
        """Close connection"""
        if self.conn and self.conn.is_connected():
            self.cursor.close()
            self.conn.close()
            print("✓ Connection closed")


# ============================================
# PRODUCT SCRAPER
# ============================================

def scrape_product(url):
    """
    Scrape complete product details:
    - Product Name
    - Price
    - Rating
    - Review Count
    - Image URL
    """
    
    print("\n" + "="*70)
    print("SCRAPING PRODUCT")
    print("="*70)
    print(f"URL: {url}\n")
    
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = None
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        driver.get(url)
        time.sleep(5)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        product_data = {'url': url}
        
        # ========== PRODUCT NAME ==========
        name_selectors = [
            ('class', 'B_NuCI'),      # Flipkart
            ('class', 'VU-ZEz'),      # Flipkart alt
            ('id', 'productTitle'),   # Amazon
            ('class', 'product-title'),
            ('tag', 'h1')
        ]
        
        for sel_type, sel_value in name_selectors:
            element = None
            if sel_type == 'id':
                element = soup.find(id=sel_value)
            elif sel_type == 'class':
                element = soup.find(class_=sel_value)
            elif sel_type == 'tag':
                element = soup.find(sel_value)
            
            if element and element.get_text().strip():
                product_data['product_name'] = element.get_text().strip()
                print(f"✓ Product Name: {product_data['product_name'][:60]}...")
                break
        
        # ========== PRICE ==========
        price_selectors = [
            ('class', '_30jeq3'),         # Flipkart
            ('class', 'Nx9bqj'),          # Flipkart alt
            ('class', '_16Jk6d'),         # Flipkart alt
            ('class', 'a-price-whole'),   # Amazon
            ('class', 'a-offscreen'),     # Amazon alt
        ]
        
        for sel_type, sel_value in price_selectors:
            element = soup.find(class_=sel_value)
            if element and element.get_text().strip():
                price_text = element.get_text().strip()
                product_data['price'] = price_text
                print(f"✓ Price: {product_data['price']}")
                break
        
        # ========== RATING ==========
        rating_selectors = [
            ('class', '_3LWZlK'),      # Flipkart
            ('class', 'XQDdHH'),       # Flipkart alt
            ('class', 'a-icon-alt'),   # Amazon
            ('class', 'a-star-4'),     # Amazon alt
        ]
        
        for sel_type, sel_value in rating_selectors:
            element = soup.find(class_=sel_value)
            if element and element.get_text().strip():
                rating_text = element.get_text().strip()
                # Extract just the number
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    product_data['rating'] = rating_match.group(1)
                else:
                    product_data['rating'] = rating_text
                print(f"✓ Rating: {product_data['rating']}")
                break
        
        # ========== REVIEW COUNT ==========
        review_selectors = [
            ('class', '_2_R_DZ'),      # Flipkart
            ('class', 'Wphh3N'),       # Flipkart alt
            ('id', 'acrCustomerReviewText'),  # Amazon
            ('class', 'a-size-base'),  # Amazon alt
        ]
        
        for sel_type, sel_value in review_selectors:
            element = None
            if sel_type == 'id':
                element = soup.find(id=sel_value)
            else:
                element = soup.find(class_=sel_value)
            
            if element:
                text = element.get_text().strip()
                # Extract number from text like "1,234 ratings" or "5,678 reviews"
                review_match = re.search(r'([\d,]+)\s*(rating|review)', text, re.IGNORECASE)
                if review_match:
                    product_data['review_count'] = review_match.group(1)
                    print(f"✓ Reviews: {product_data['review_count']}")
                    break
        
        # ========== IMAGE URL ==========
        # Try main product image selectors first
        image_found = False
        
        # Flipkart - Look for main product image container
        image_containers = soup.find_all('div', class_='_2Pvyxl')
        if not image_found and image_containers:
            for container in image_containers:
                img = container.find('img')
                if img:
                    img_url = img.get('src') or img.get('data-src')
                    if img_url and img_url.startswith('http') and 'rukminim' in img_url:
                        product_data['image_url'] = img_url
                        print(f"✓ Image URL: {product_data['image_url'][:60]}...")
                        image_found = True
                        break
        
        # Try other Flipkart selectors
        if not image_found:
            image_selectors = [
                ('class', '_396cs4'),
                ('class', '_53J4C-'),
                ('class', 'CXW8mj'),
            ]
            
            for sel_type, sel_value in image_selectors:
                element = soup.find('img', class_=sel_value)
                if element:
                    img_url = element.get('src') or element.get('data-src')
                    if img_url and img_url.startswith('http') and 'rukminim' in img_url:
                        product_data['image_url'] = img_url
                        print(f"✓ Image URL: {product_data['image_url'][:60]}...")
                        image_found = True
                        break
        
        # Amazon selectors
        if not image_found:
            amazon_selectors = [
                ('id', 'landingImage'),
                ('class', 'a-dynamic-image'),
            ]
            
            for sel_type, sel_value in amazon_selectors:
                element = None
                if sel_type == 'id':
                    element = soup.find('img', id=sel_value)
                else:
                    element = soup.find('img', class_=sel_value)
                
                if element:
                    img_url = element.get('src') or element.get('data-src')
                    if img_url and img_url.startswith('http'):
                        product_data['image_url'] = img_url
                        print(f"✓ Image URL: {product_data['image_url'][:60]}...")
                        image_found = True
                        break
        
        # Last resort - find largest product image
        if not image_found:
            all_images = soup.find_all('img')
            best_img = None
            best_size = 0
            
            for img in all_images:
                img_url = img.get('src') or img.get('data-src')
                if img_url and img_url.startswith('http'):
                    # Check if it's a product image (contains specific domains)
                    if any(domain in img_url for domain in ['rukminim', 'm.media-amazon', 'images-na.ssl-images-amazon']):
                        # Try to get image size from URL or attributes
                        width = img.get('width')
                        height = img.get('height')
                        
                        try:
                            size = int(width or 0) * int(height or 0)
                            if size > best_size:
                                best_size = size
                                best_img = img_url
                        except:
                            # If no size info, check URL for resolution
                            if '/400/' in img_url or '/500/' in img_url or '/612/' in img_url:
                                best_img = img_url
            
            if best_img:
                product_data['image_url'] = best_img
                print(f"✓ Image URL: {product_data['image_url'][:60]}...")
                image_found = True
        
        # Set defaults for missing data
        if 'product_name' not in product_data:
            product_data['product_name'] = 'Product name not found'
            print("⚠ Product name not found")
        
        if 'price' not in product_data:
            product_data['price'] = 'Price not found'
            print("⚠ Price not found")
        
        if 'rating' not in product_data:
            product_data['rating'] = 'N/A'
            print("⚠ Rating not found")
        
        if 'review_count' not in product_data:
            product_data['review_count'] = 'N/A'
            print("⚠ Review count not found")
        
        if 'image_url' not in product_data:
            product_data['image_url'] = 'Image not found'
            print("⚠ Image not found")
        
        # Save debug file
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print("\n" + "="*70)
        print("EXTRACTION COMPLETE")
        print("="*70)
        
        return product_data
        
    except Exception as e:
        print(f"\n✗ Scraping Error: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        if driver:
            driver.quit()


# ============================================
# MAIN PROGRAM
# ============================================

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║      COMPLETE PRODUCT SCRAPER WITH MySQL                 ║
    ║  Extracts: Name, Price, Rating, Reviews, Image           ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Connect and setup (credentials are already in ProductDatabase class)
    db = ProductDatabase('localhost', 'root', 'Mehulmysql@90', 'project_smart')
    
    if not db.connect():
        print("✗ Connection failed!")
        return
    
    if not db.setup_table():
        print("✗ Table setup failed!")
        return
    
    # Main menu
    while True:
        print("\n" + "="*60)
        print("MENU")
        print("="*60)
        print("1. Scrape product(s)")
        print("2. View all products")
        print("3. Export to CSV")
        print("4. Exit")
        print("="*60)
        
        choice = input("\nChoice: ").strip()
        
        if choice == '1':
            urls = []
            print("\nEnter URLs (type 'done' to finish):")
            while True:
                url = input(f"URL {len(urls)+1}: ").strip()
                if url.lower() == 'done' or url == '':
                    break
                urls.append(url)
            
            if urls:
                success = 0
                for i, url in enumerate(urls, 1):
                    print(f"\n{'='*60}")
                    print(f"Product {i}/{len(urls)}")
                    print('='*60)
                    
                    product_data = scrape_product(url)
                    if product_data and db.insert_product(product_data):
                        success += 1
                    
                    if i < len(urls):
                        print("\n⏳ Waiting 5 seconds...")
                        time.sleep(5)
                
                print(f"\n✅ Saved {success}/{len(urls)} products!")
        
        elif choice == '2':
            db.display_products()
        
        elif choice == '3':
            filename = input("Filename (products_export.csv): ").strip() or 'products_export.csv'
            db.export_to_csv(filename)
        
        elif choice == '4':
            db.close()
            print("\n👋 Goodbye!")
            break


if __name__ == "__main__":
    main()