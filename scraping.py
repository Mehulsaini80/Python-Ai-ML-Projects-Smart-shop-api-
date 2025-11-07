"""
TEST FILE - Run this first to verify setup
"""

print("Testing library installations...")
print("-" * 50)

# Test 1: Check if libraries are installed
try:
    import requests
    print("✓ requests installed")
except ImportError:
    print("✗ requests NOT installed - Run: pip install requests")

try:
    from bs4 import BeautifulSoup 
    print("✓ BeautifulSoup installed")
except ImportError:
    print("✗ BeautifulSoup NOT installed - Run: pip install beautifulsoup4")

try:
    import pandas
    print("✓ pandas installed")
except ImportError:
    print("✗ pandas NOT installed - Run: pip install pandas")

try:
    from selenium import webdriver
    print("✓ Selenium installed")
except ImportError:
    print("✗ Selenium NOT installed - Run: pip install selenium")

print("\n" + "=" * 50)
print("Testing Selenium & ChromeDriver...")
print("=" * 50)

# Test 2: Check if ChromeDriver works
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    print("\nAttempting to start Chrome driver...")
    driver = webdriver.Chrome(options=chrome_options)
    
    print("✓ ChromeDriver is working!")
    
    # Test with a simple website
    print("\nTesting with example.com...")
    driver.get("https://example.com")
    print(f"✓ Successfully loaded: {driver.title}")
    
    driver.quit()
    print("\n✅ ALL TESTS PASSED! You're ready to scrape!")
    
except Exception as e:
    print(f"\n✗ ChromeDriver Error: {e}")
    print("\nPossible fixes:")
    print("1. Download ChromeDriver from: https://chromedriver.chromium.org/")
    print("2. Make sure ChromeDriver version matches your Chrome browser")
    print("3. Place chromedriver.exe in the same folder as this script")
    print("4. Or add ChromeDriver location to system PATH")

print("\n" + "=" * 50)
print("Setup check complete!")
print("=" * 50)