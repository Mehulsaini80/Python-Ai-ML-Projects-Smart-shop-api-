"""
Simple Product Scraper - Ready to Use
=====================================
Works for Amazon, Flipkart, and most e-commerce sites
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import pandas as pd

def scrape_product(url):
    """
    Scrape product details from e-commerce site
    """
    print("="*60)
    print("Starting Product Scraper...")
    print("="*60)
    print(f"\nURL: {url}\n")
    
    # Configure Chrome
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Uncomment to hide browser window
    # chrome_options.add_argument('--headless')
    
    try:
        print("Opening browser...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        print("Loading page...")
        driver.get(url)
        
        # Wait for page to load 
        time.sleep(5)
        
        print("Page loaded! Extracting data...\n")
        
        # Get page source
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        # Save HTML for inspection
        with open('page_source.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✓ Saved page source to 'page_source.html'")
        
        # Extract product data
        product_data = {}
        
        # Try different selectors for Amazon
        print("\nAttempting to extract product details...")
        
        # Title
        title_selectors = [
            ('id', 'productTitle'),
            ('class', 'product-title-word-break'),
            ('class', 'B_NuCI'),  # Flipkart
            ('tag', 'h1')
        ]
        
        for selector_type, selector_value in title_selectors:
            try:
                if selector_type == 'id':
                    element = soup.find(id=selector_value)
                elif selector_type == 'class':
                    element = soup.find(class_=selector_value)
                elif selector_type == 'tag':
                    element = soup.find(selector_value)
                
                if element:
                    product_data['title'] = element.get_text().strip()
                    print(f"✓ Title: {product_data['title'][:60]}...")
                    break
            except:
                continue
        
        # Price
        price_selectors = [
            ('class', 'a-price-whole'),
            ('class', '_30jeq3'),  # Flipkart
            ('class', 'price'),
        ]
        
        for selector_type, selector_value in price_selectors:
            try:
                if selector_type == 'class':
                    element = soup.find(class_=selector_value)
                
                if element:
                    product_data['price'] = element.get_text().strip()
                    print(f"✓ Price: {product_data['price']}")
                    break
            except:
                continue
        
        # Rating
        rating_selectors = [
            ('class', 'a-icon-alt'),
            ('class', '_3LWZlK'),  # Flipkart
        ]
        
        for selector_type, selector_value in rating_selectors:
            try:
                if selector_type == 'class':
                    element = soup.find(class_=selector_value)
                
                if element:
                    product_data['rating'] = element.get_text().strip()
                    print(f"✓ Rating: {product_data['rating']}")
                    break
            except:
                continue
        
        # Get all text content for analysis
        page_text = soup.get_text()
        
        # Additional info
        product_data['url'] = url
        product_data['scraped_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Close browser
        driver.quit()
        print("\n✓ Browser closed")
        
        # Save results
        print("\nSaving results...")
        
        # Save as JSON
        with open('product_data.json', 'w', encoding='utf-8') as f:
            json.dump(product_data, f, indent=2, ensure_ascii=False)
        print("✓ Saved to product_data.json")
        
        # Save as CSV
        df = pd.DataFrame([product_data])
        df.to_csv('product_data.csv', index=False, encoding='utf-8')
        print("✓ Saved to product_data.csv")
        
        # Display results
        print("\n" + "="*60)
        print("SCRAPING COMPLETE!")
        print("="*60)
        print("\nExtracted Data:")
        print("-"*60)
        for key, value in product_data.items():
            print(f"{key}: {value}")
        
        print("\n" + "="*60)
        print("\nNOTE: If some data is missing:")
        print("1. Open 'page_source.html' in browser")
        print("2. Find the element you want")
        print("3. Note its class/id")
        print("4. Add it to the selectors in this script")
        print("="*60)
        
        return product_data
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        try:
            driver.quit()
        except:
            pass
        return None


def scrape_multiple_products(urls):
    """
    Scrape multiple product URLs
    """
    all_products = []
    
    for i, url in enumerate(urls, 1):
        print(f"\n\n{'='*60}")
        print(f"Product {i}/{len(urls)}")
        print('='*60)
        
        product = scrape_product(url)
        if product:
            all_products.append(product)
        
        # Delay between products
        if i < len(urls):
            print("\nWaiting 5 seconds before next product...")
            time.sleep(5)
    
    # Save all products
    if all_products:
        df = pd.DataFrame(all_products)
        df.to_csv('all_products.csv', index=False, encoding='utf-8')
        print(f"\n✓ Saved {len(all_products)} products to all_products.csv")
    
    return all_products


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║           PRODUCT SCRAPER - READY TO USE               ║
    ╚════════════════════════════════════════════════════════╝
    
    This script will:
    1. Open the product page in Chrome
    2. Extract product details (title, price, rating)
    3. Save the data to JSON and CSV files
    4. Save the page HTML for inspection
    
    """)
    
    # Get URL from user
    print("Enter product URL(s):")
    print("(Press Enter after each URL, type 'done' when finished)\n")
    
    urls = []
    while True:
        url = input(f"URL {len(urls)+1}: ").strip()
        if url.lower() == 'done' or url == '':
            break
        urls.append(url)
    
    if urls:
        if len(urls) == 1:
            scrape_product(urls[0])
        else:
            scrape_multiple_products(urls)
    else:
        print("\n⚠ No URLs provided!")
        print("\nExample usage:")
        print("python simple_scraper.py")
        print("\nThen paste Amazon/Flipkart product URLs when prompted") 