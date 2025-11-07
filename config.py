# API Configuration
API_KEYS = {
    'amazon_api': '609ebc6c42437df2aa0bc137c9fee442',
    'flipkart_api': 'bb96fc3b2cmshc717cd4dcdc1e14p162ff0jsn63e6332bdc9d'  
}

RAPIDAPI_ENDPOINTS = {
    'amazon_search': 'https://real-time-amazon-data.p.rapidapi.com/search',
    'flipkart_search': 'https://flipkart-scraper-api.p.rapidapi.com/product/search'
}

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Mehulmysql@90',
    'database': 'project_smart'
}

# Constants
USD_TO_INR = 82.0
API_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3

# Platform priority for best deal calculation
PLATFORM_PRIORITY = ['Amazon', 'Flipkart', 'Myntra', 'AJIO', 'Meesho']

# Comparison Settings
COMPARISON_SETTINGS = {
    'show_images': False,  # Disable images in comparison
    'max_products_per_platform': 20,  # Limit results
    'min_discount_threshold': 0,  # Show all discounts
    'relevance_score_threshold': 0.4  # Minimum relevance match
}