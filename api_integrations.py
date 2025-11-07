import requests
import json
from datetime import datetime, timedelta
import mysql.connector
from typing import List, Dict, Optional
import pandas as pd
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import API_KEYS, RAPIDAPI_ENDPOINTS, DB_CONFIG, USD_TO_INR, API_TIMEOUT_SECONDS, MAX_RETRIES, COMPARISON_SETTINGS

class MultiPlatformAPIIntegration:
    """Handles real-time product data from multiple e-commerce platforms"""
    
    def __init__(self):
        self.api_keys = API_KEYS
        self.cache_duration = 6  # hours
        self.usd_to_inr = USD_TO_INR
        self.last_api_calls = {}  # Track per-platform
        self.api_call_delay = 1.5  # seconds between calls
        self.show_images = COMPARISON_SETTINGS['show_images']
    
    def _rate_limit_delay(self, platform: str):
        """Implement rate limiting per platform"""
        if platform in self.last_api_calls:
            elapsed = (datetime.now() - self.last_api_calls[platform]).total_seconds()
            if elapsed < self.api_call_delay:
                time.sleep(self.api_call_delay - elapsed)
        self.last_api_calls[platform] = datetime.now()
    
    def search_amazon_products(self, query: str, min_price: float = None, max_price: float = None) -> List[Dict]:
        """Search products on Amazon"""
        print(f"\n🔍 Searching Amazon for: {query}")
        
        # Check cache first
        cached = self._get_cached_products(query, 'Amazon', min_price, max_price)
        if cached and len(cached) >= 5:
            print(f"💾 Using {len(cached)} cached Amazon products")
            return cached
        
        self._rate_limit_delay('Amazon')
        
        headers = {
            'X-RapidAPI-Key': self.api_keys['amazon_api'],
            'X-RapidAPI-Host': 'real-time-amazon-data.p.rapidapi.com'
        }
        
        params = {
            'query': query,
            'page': '1',
            'country': 'IN',
            'sort_by': 'RELEVANCE',
            'product_condition': 'ALL'
        }
        
        if min_price:
            params['min_price'] = str(int(min_price))
        if max_price:
            params['max_price'] = str(int(max_price))
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(
                    RAPIDAPI_ENDPOINTS['amazon_search'],
                    headers=headers,
                    params=params,
                    timeout=API_TIMEOUT_SECONDS
                )
                
                if response.status_code == 200:
                    data = response.json()
                    products = self._parse_amazon_response(data, query)
                    
                    if products:
                        print(f"✅ Amazon: {len(products)} products found")
                        self._cache_api_results(query, products, 'Amazon', min_price, max_price)
                        return products
                    else:
                        print("⚠️ No Amazon products parsed")
                        return self._get_mock_products(query, min_price or 10000, 'Amazon', count=10)
                
                elif response.status_code == 429:
                    print(f"⚠️ Amazon Rate limit - Attempt {attempt + 1}/{MAX_RETRIES}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                    return self._get_mock_products(query, min_price or 10000, 'Amazon', count=10)
                
                else:
                    print(f"❌ Amazon API Error {response.status_code}")
                    return self._get_mock_products(query, min_price or 10000, 'Amazon', count=10)
                    
            except Exception as e:
                print(f"❌ Amazon Error: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2)
                    continue
                return self._get_mock_products(query, min_price or 10000, 'Amazon', count=10)
        
        return self._get_mock_products(query, min_price or 10000, 'Amazon', count=10)
    
    def search_flipkart_products(self, query: str, min_price: float = None, max_price: float = None) -> List[Dict]:
        """Search products on Flipkart"""
        print(f"\n🔍 Searching Flipkart for: {query}")
        
        # Check cache first
        cached = self._get_cached_products(query, 'Flipkart', min_price, max_price)
        if cached and len(cached) >= 5:
            print(f"💾 Using {len(cached)} cached Flipkart products")
            return cached
        
        self._rate_limit_delay('Flipkart')
        
        headers = {
            'X-RapidAPI-Key': self.api_keys['flipkart_api'],
            'X-RapidAPI-Host': 'real-time-flipkart-data2.p.rapidapi.com'
        }
        
        params = {
            'query': query,
            'page': '1'
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(
                    RAPIDAPI_ENDPOINTS['flipkart_search'],
                    headers=headers,
                    params=params,
                    timeout=API_TIMEOUT_SECONDS
                )
                
                if response.status_code == 200:
                    data = response.json()
                    products = self._parse_flipkart_response(data, query)
                    
                    if products:
                        print(f"✅ Flipkart: {len(products)} products found")
                        self._cache_api_results(query, products, 'Flipkart', min_price, max_price)
                        return products
                    else:
                        print("⚠️ No Flipkart products parsed, using mock data")
                        return self._get_mock_products(query, min_price or 10000, 'Flipkart', count=10)
                
                elif response.status_code == 429:
                    print(f"⚠️ Flipkart Rate limit - Attempt {attempt + 1}/{MAX_RETRIES}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                    return self._get_mock_products(query, min_price or 10000, 'Flipkart', count=10)
                
                else:
                    print(f"⚠️ Flipkart API unavailable ({response.status_code}), using mock data")
                    return self._get_mock_products(query, min_price or 10000, 'Flipkart', count=10)
                    
            except Exception as e:
                print(f"⚠️ Flipkart Error: {e}, using mock data")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2)
                    continue
                return self._get_mock_products(query, min_price or 10000, 'Flipkart', count=10)
        
        return self._get_mock_products(query, min_price or 10000, 'Flipkart', count=10)
    
    def compare_products(self, query: str, max_price: float = None) -> Dict:
        """
        🎯 MAIN METHOD: Compare products across Amazon & Flipkart
        Returns unified comparison results without images
        """
        print(f"\n{'='*70}")
        print(f"🎯 MULTI-PLATFORM PRODUCT COMPARISON")
        print(f"{'='*70}")
        print(f"Query: {query}")
        print(f"Max Price: ₹{max_price:,.0f}" if max_price else "Max Price: No limit")
        print(f"Image Display: {'Enabled' if self.show_images else 'Disabled'}")
        print(f"{'='*70}\n")
        
        min_price = None
        if max_price:
            min_price = max_price * 0.3  # 30% of max price as minimum
        
        # Fetch from both platforms in parallel
        all_products = []
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_amazon = executor.submit(self.search_amazon_products, query, min_price, max_price)
            future_flipkart = executor.submit(self.search_flipkart_products, query, min_price, max_price)
            
            amazon_products = future_amazon.result()
            flipkart_products = future_flipkart.result()
        
        all_products.extend(amazon_products)
        all_products.extend(flipkart_products)
        
        # Filter by price if specified
        if max_price:
            all_products = [p for p in all_products if p['discounted_price'] <= max_price]
        
        print(f"\n📊 COMPARISON RESULTS:")
        print(f"   Amazon Products: {len(amazon_products)}")
        print(f"   Flipkart Products: {len(flipkart_products)}")
        print(f"   Total Products: {len(all_products)}")
        
        # Calculate statistics
        result = {
            'products': all_products,
            'total_count': len(all_products),
            'amazon_count': len(amazon_products),
            'flipkart_count': len(flipkart_products),
            'show_images': self.show_images
        }
        
        if all_products:
            # Best deal (lowest price)
            result['best_deal'] = min(all_products, key=lambda x: x['discounted_price'])
            
            # Highest discount product
            result['highest_discount'] = max(all_products, key=lambda x: x['discount_percent'])
            
            # Platform with most discounts on average
            platform_stats = self._calculate_platform_stats(all_products)
            result['platform_stats'] = platform_stats
            
            # Best platform overall (highest avg discount)
            if platform_stats:
                result['best_platform'] = max(
                    platform_stats.items(),
                    key=lambda x: x[1]['avg_discount']
                )[0]
            else:
                result['best_platform'] = None
            
            print(f"\n🏆 BEST DEAL: {result['best_deal']['product_name'][:50]}...")
            print(f"   Platform: {result['best_deal']['platform']}")
            print(f"   Price: ₹{result['best_deal']['discounted_price']:,.0f}")
            print(f"   Discount: {result['best_deal']['discount_percent']:.1f}%")
            
            print(f"\n💰 HIGHEST DISCOUNT: {result['highest_discount']['product_name'][:50]}...")
            print(f"   Platform: {result['highest_discount']['platform']}")
            print(f"   Discount: {result['highest_discount']['discount_percent']:.1f}%")
            
            if result['best_platform']:
                print(f"\n🎯 BEST PLATFORM OVERALL: {result['best_platform']}")
                print(f"   Avg Discount: {platform_stats[result['best_platform']]['avg_discount']:.1f}%")
                print(f"   Products Found: {platform_stats[result['best_platform']]['product_count']}")
        
        print(f"\n{'='*70}\n")
        
        return result
    
    def _calculate_platform_stats(self, products: List[Dict]) -> Dict:
        """Calculate comprehensive statistics per platform"""
        stats = {}
        
        platforms = set(p['platform'] for p in products)
        
        for platform in platforms:
            platform_products = [p for p in products if p['platform'] == platform]
            
            if platform_products:
                stats[platform] = {
                    'product_count': len(platform_products),
                    'avg_discount': sum(p['discount_percent'] for p in platform_products) / len(platform_products),
                    'lowest_price': min(p['discounted_price'] for p in platform_products),
                    'highest_discount': max(p['discount_percent'] for p in platform_products),
                    'avg_price': sum(p['discounted_price'] for p in platform_products) / len(platform_products),
                    'total_savings': sum((p['price'] - p['discounted_price']) for p in platform_products)
                }
        
        return stats
    
    def _parse_amazon_response(self, data: dict, query: str) -> List[Dict]:
        """Parse Amazon API response - optimized for comparison"""
        products = []
        
        product_list = []
        if isinstance(data, dict):
            if 'data' in data:
                if isinstance(data['data'], dict) and 'products' in data['data']:
                    product_list = data['data']['products']
                elif isinstance(data['data'], list):
                    product_list = data['data']
            elif 'products' in data:
                product_list = data['products']
        
        for item in product_list[:COMPARISON_SETTINGS['max_products_per_platform']]:
            try:
                if not isinstance(item, dict):
                    continue
                
                product_name = (
                    item.get('product_title') or 
                    item.get('title') or 
                    item.get('name') or ''
                ).strip()
                
                if len(product_name) < 3:
                    continue
                
                price_str = str(item.get('product_price', '') or item.get('price', '') or '0')
                price_match = re.search(r'([\d,]+\.?\d*)', price_str)
                if not price_match:
                    continue
                
                current_price = float(price_match.group(1).replace(',', ''))
                
                if '$' in price_str or current_price < 100:
                    current_price = current_price * self.usd_to_inr
                
                if current_price < 10 or current_price > 1000000:
                    continue
                
                original_price_str = str(item.get('product_original_price', '') or '0')
                original_match = re.search(r'([\d,]+\.?\d*)', original_price_str)
                
                if original_match:
                    original_price = float(original_match.group(1).replace(',', ''))
                    if '$' in original_price_str:
                        original_price = original_price * self.usd_to_inr
                    if original_price <= current_price:
                        original_price = current_price * 1.20
                else:
                    original_price = current_price * 1.20
                
                discount_percent = ((original_price - current_price) / original_price) * 100
                
                rating_str = str(item.get('product_star_rating', '') or item.get('rating', '') or '4.0')
                rating_match = re.search(r'([\d.]+)', rating_str)
                rating = float(rating_match.group(1)) if rating_match else 4.0
                rating = max(1.0, min(5.0, rating))
                
                # Only include image URL if show_images is enabled
                image_url = ''
                if self.show_images:
                    image_url = (
                        item.get('product_photo') or 
                        item.get('image') or 
                        ''
                    )
                
                product_url = (
                    item.get('product_url') or 
                    item.get('link') or 
                    f'https://www.amazon.in/s?k={query.replace(" ", "+")}'
                )
                
                product = {
                    'platform': 'Amazon',
                    'product_name': product_name[:200],
                    'category': query.title(),
                    'price': round(original_price, 2),
                    'discounted_price': round(current_price, 2),
                    'discount_percent': round(discount_percent, 2),
                    'rating': round(rating, 1),
                    'stock': random.randint(50, 200),
                    'product_url': product_url,
                    'image_url': image_url,
                    'sku': item.get('asin', f"AMZ{random.randint(1000, 9999)}"),
                    'savings': round(original_price - current_price, 2)
                }
                
                if (product['discounted_price'] >= 10 and 
                    product['discount_percent'] >= COMPARISON_SETTINGS['min_discount_threshold'] and 
                    product['discount_percent'] <= 90):
                    products.append(product)
                
            except Exception as e:
                continue
        
        return products
    
    def _parse_flipkart_response(self, data: dict, query: str) -> List[Dict]:
        """Parse Flipkart API response - optimized for comparison"""
        products = []
        
        product_list = []
        if isinstance(data, dict):
            if 'products' in data:
                product_list = data['products']
            elif 'data' in data and isinstance(data['data'], list):
                product_list = data['data']
            elif 'results' in data:
                product_list = data['results']
        
        for item in product_list[:COMPARISON_SETTINGS['max_products_per_platform']]:
            try:
                if not isinstance(item, dict):
                    continue
                
                product_name = (
                    item.get('name') or 
                    item.get('title') or 
                    item.get('product_name') or ''
                ).strip()
                
                if len(product_name) < 3:
                    continue
                
                current_price = float(item.get('current_price', 0) or item.get('price', 0) or 0)
                original_price = float(item.get('original_price', 0) or item.get('mrp', 0) or 0)
                
                if current_price < 10:
                    continue
                
                if original_price <= current_price:
                    original_price = current_price * 1.25
                
                discount_percent = ((original_price - current_price) / original_price) * 100
                
                rating = float(item.get('rating', 4.0) or 4.0)
                rating = max(1.0, min(5.0, rating))
                
                # Only include image URL if show_images is enabled
                image_url = ''
                if self.show_images:
                    image_url = (
                        item.get('image') or 
                        item.get('thumbnail') or 
                        ''
                    )
                
                product_url = (
                    item.get('link') or 
                    item.get('url') or 
                    f'https://www.flipkart.com/search?q={query.replace(" ", "+")}'
                )
                
                product = {
                    'platform': 'Flipkart',
                    'product_name': product_name[:200],
                    'category': query.title(),
                    'price': round(original_price, 2),
                    'discounted_price': round(current_price, 2),
                    'discount_percent': round(discount_percent, 2),
                    'rating': round(rating, 1),
                    'stock': random.randint(50, 200),
                    'product_url': product_url,
                    'image_url': image_url,
                    'sku': item.get('id', f"FLP{random.randint(1000, 9999)}"),
                    'savings': round(original_price - current_price, 2)
                }
                
                if (product['discounted_price'] >= 10 and 
                    product['discount_percent'] >= COMPARISON_SETTINGS['min_discount_threshold'] and 
                    product['discount_percent'] <= 90):
                    products.append(product)
                
            except Exception as e:
                continue
        
        return products
    
    def _get_mock_products(self, category: str, budget: float, platform: str, count: int = 10) -> List[Dict]:
        """Generate realistic mock products for a specific platform"""
        products = []
        
        product_templates = {
            'laptop': ['Dell Inspiron', 'HP Pavilion', 'Lenovo IdeaPad', 'ASUS VivoBook', 'Acer Aspire'],
            'mobile': ['iPhone 13', 'Samsung Galaxy S21', 'OnePlus 9', 'Xiaomi Redmi Note', 'Vivo V21'],
            'headphone': ['Sony WH-1000XM4', 'Boat Rockerz', 'JBL Tune', 'boAt Airdopes', 'Realme Buds'],
            'watch': ['Apple Watch', 'Samsung Galaxy Watch', 'Noise ColorFit', 'Fire-Boltt', 'Amazfit'],
            'shoe': ['Nike Air Max', 'Adidas Ultraboost', 'Puma RS-X', 'Reebok Classic', 'Skechers'],
        }
        
        category_lower = category.lower()
        names = None
        for key, templates in product_templates.items():
            if key in category_lower:
                names = templates
                break
        
        if not names:
            names = [f'{category} Product']
        
        for i in range(count):
            base_price = budget * random.uniform(0.7, 1.3)
            discount = random.uniform(10, 45) if platform == 'Flipkart' else random.uniform(5, 40)
            discounted_price = base_price * (1 - discount/100)
            
            product = {
                'platform': platform,
                'product_name': f"{random.choice(names)} {random.choice(['Pro', 'Plus', 'Max', 'Lite', 'SE', ''])}".strip(),
                'category': category,
                'price': round(base_price, 2),
                'discounted_price': round(discounted_price, 2),
                'discount_percent': round(discount, 2),
                'rating': round(random.uniform(3.8, 4.9), 1),
                'stock': random.randint(20, 300),
                'product_url': f'https://{platform.lower()}.com/product-{i}',
                'image_url': '' if not self.show_images else f'https://via.placeholder.com/300x200?text={platform}',
                'sku': f'{platform[:3].upper()}{1000+i}',
                'savings': round(base_price - discounted_price, 2)
            }
            products.append(product)
        
        return products
    
    def _cache_api_results(self, query: str, products: List[Dict], platform: str, 
                          min_price: float = None, max_price: float = None):
        """Cache API results to database"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM product_cache 
                WHERE category = %s AND platform = %s 
                AND cached_at < NOW() - INTERVAL 6 HOUR
            """, (query, platform))
            
            for product in products:
                try:
                    cursor.execute("""
                        INSERT INTO product_cache 
                        (platform, product_name, category, price, discounted_price, 
                         discount_percent, rating, stock, image_url, product_url, cached_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                        price = VALUES(price),
                        discounted_price = VALUES(discounted_price),
                        discount_percent = VALUES(discount_percent),
                        cached_at = NOW()
                    """, (
                        product['platform'],
                        product['product_name'],
                        query,
                        product['price'],
                        product['discounted_price'],
                        product['discount_percent'],
                        product['rating'],
                        product['stock'],
                        product.get('image_url', ''),
                        product.get('product_url', '')
                    ))
                except:
                    continue
            
            conn.commit()
            cursor.close()
            conn.close()
            print(f"💾 Cached {len(products)} {platform} products")
        except Exception as e:
            print(f"⚠️ Cache error: {e}")
    
    def _get_cached_products(self, query: str, platform: str, 
                           min_price: float = None, max_price: float = None) -> List[Dict]: 
        """Get cached products"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            
            sql = """
                SELECT * FROM product_cache
                WHERE category = %s AND platform = %s
                AND cached_at > NOW() - INTERVAL 6 HOUR
            """
            params = [query, platform]
            
            if min_price:
                sql += " AND price >= %s"
                params.append(min_price)
            
            if max_price: 
                sql += " AND price <= %s"
                params.append(max_price)
            
            sql += " LIMIT 30"
            
            cursor.execute(sql, params)
            products = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Remove image_url if images are disabled
            if not self.show_images:
                for product in products:
                    product['image_url'] = ''
            
            return products if products else []
        except Exception as e:
            return []


# Backward compatibility
class ProductAPIIntegration(MultiPlatformAPIIntegration):
    """Legacy class for backward compatibility"""
    pass