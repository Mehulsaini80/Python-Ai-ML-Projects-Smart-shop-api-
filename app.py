from flask import Flask, render_template, request, jsonify, redirect, session
from flask_cors import CORS
import mysql.connector
import pickle
import numpy as np
import os 
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Dict, List, Optional

app = Flask(__name__)
app.secret_key = 'App_login_data'  
CORS(app, supports_credentials=True, origins=['http://localhost:5000'])       
# Add these lines:
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False 
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

print("\nLoading ML models...") 
try:
    with open('label_encoders.pkl', 'rb') as f: 
        label_encoders = pickle.load(f) 
        
    with open('platform_model.pkl', 'rb') as f:
        platform_model = pickle.load(f)
        
    with open('platform_scaler.pkl', 'rb') as f:
        platform_scaler = pickle.load(f)
        
    with open('discount_model.pkl', 'rb') as f:
        discount_model = pickle.load(f)
        
    with open('discount_scaler.pkl', 'rb') as f:
        discount_scaler = pickle.load(f)
        
    with open('model_metadata.pkl', 'rb') as f:
        model_metadata = pickle.load(f)
    
    models_loaded = True
    print("✅ ML models loaded successfully!")
except Exception as e:
    models_loaded = False
    model_metadata = None
    print(f"❌ Error loading ML models: {e}")
    print("⚠️ Please run model_training.py first to train and save the models.")

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Mehulmysql@90',
    'database': 'project_smart' 
} 

ADMIN_CREDENTIALS = {
    'username': 'admin',
    'password': 'admin123'  
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("✅ Database connected successfully")
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Database connection failed: {err}")
        raise 


@app.route('/admin/login')
def admin_login_page():
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect('/admin/login')
    return render_template('admin.html')

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect('/admin/login')




@app.route('/api/admin/stats')
def admin_stats():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401 
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total_users = cursor.fetchone()['count']
        except Exception as e:
            print(f"⚠️ Error counting users: {e}")
            total_users = 0
        
        try:
            cursor.execute("SELECT COUNT(*) as count FROM products")
            total_products = cursor.fetchone()['count']
        except Exception as e:
            print(f"⚠️ Error counting products: {e}")
            total_products = 0
        
        try:
            cursor.execute("SHOW TABLES LIKE 'predictions'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                cursor.execute("SELECT COUNT(*) as count FROM predictions")
                total_predictions = cursor.fetchone()['count']
            else:
                print("⚠️ Predictions table doesn't exist yet")
                total_predictions = 0
        except Exception as e:
            print(f"⚠️ Error counting predictions: {e}")
            total_predictions = 0
        
        recent_predictions = []
        try:
            cursor.execute("SHOW TABLES LIKE 'predictions'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                cursor.execute("""
                    SELECT 
                        id,
                        user_email,
                        category,
                        budget,
                        platform,
                        predicted_discount,
                        predicted_platform,
                        created_at
                    FROM predictions 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """)
                recent_predictions = cursor.fetchall()
        except Exception as e:
            print(f"⚠️ Error fetching recent predictions: {e}")
            recent_predictions = []
        
        cursor.close()
        conn.close()
        
        print(f"✅ Stats loaded: {total_users} users, {total_products} products, {total_predictions} predictions")
        
        return jsonify({
            'success': True,
            'stats': {
                'users': total_users,
                'products': total_products,
                'predictions': total_predictions
            },
            'recent_predictions': recent_predictions
        })
        
    except Exception as e:
        print(f"❌ Error in admin stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': str(e)
        }, 500)

@app.route('/api/admin/users')
def admin_get_users():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/products')
def admin_get_products():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                product_id as id,
                product_name as name,
                category,
                platform,
                price,
                discount_percent,
                discounted_price,
                rating,
                stock
            FROM products 
            ORDER BY product_id DESC
        """)
        
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print(f"✅ Successfully loaded {len(products)} products")  # Debug log
        
        return jsonify({
            'success': True, 
            'products': products
        })
        
    except mysql.connector.Error as db_error:
        print(f"❌ Database error: {db_error}")
        return jsonify({
            'success': False, 
            'error': f'Database error: {str(db_error)}'
        }), 500
        
    except Exception as e:
        print(f"❌ General error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500
        
        
@app.route('/api/admin/products/<int:product_id>', methods=['GET'])
def admin_get_product(product_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                product_id as id,
                product_name as name,
                category,
                platform,
                price,
                discount_percent,
                discounted_price,
                rating,
                stock
            FROM products 
            WHERE product_id = %s
        """, (product_id,))
        
        product = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if product:
            print(f"✅ Fetched product ID: {product_id}")
            return jsonify({'success': True, 'product': product})
        else:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
            
    except Exception as e:
        print(f"❌ Error fetching product: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    
@app.route('/api/admin/products/<int:product_id>', methods=['PUT'])
def admin_update_product(product_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE products 
            SET product_name = %s,
                category = %s,
                platform = %s,
                price = %s,
                discount_percent = %s,
                discounted_price = %s,
                rating = %s,
                stock = %s
            WHERE product_id = %s
        """, (
            data['name'],
            data['category'],
            data['platform'],
            float(data['price']),
            float(data['discount_percent']),
            float(data['discounted_price']),
            float(data.get('rating', 4.0)),
            int(data.get('stock', 100)),
            product_id
        ))
        
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        conn.close()
        
        if affected_rows > 0:
            print(f"✅ Updated product ID: {product_id}")
            return jsonify({'success': True, 'message': 'Product updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
        
    except Exception as e:
        print(f"❌ Error updating product: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
    
    
@app.route('/api/admin/products/test')
def test_products():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products LIMIT 5")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'count': len(products), 'products': products})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    
    

@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
def admin_delete_product(product_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
        conn.commit()
        
        deleted_rows = cursor.rowcount
        cursor.close()
        conn.close()
        
        if deleted_rows > 0:
            print(f"✅ Deleted product ID: {product_id}")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
            
    except Exception as e:
        print(f"❌ Error deleting product: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    

@app.route('/api/admin/products/add', methods=['POST'])
def admin_add_product():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401 
    
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        import random 
        sku = f"{data['platform'][:2].upper()}{random.randint(1000, 9999)}"
        
        cursor.execute("""
            INSERT INTO products 
            (platform, sku, product_name, category, price, discount_percent, 
             discounted_price, rating, stock)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['platform'],
            sku,
            data['name'],
            data['category'],
            data['price'],
            data['discount_percent'],
            data['discounted_price'],
            data.get('rating', 4.0),
            data.get('stock', 100)
        ))
        
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        print(f"✅ Added new product ID: {new_id}")
        return jsonify({'success': True, 'product_id': new_id})
        
    except Exception as e:
        print(f"❌ Error adding product: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    

# ===== PRODUCT CARD GENERATOR API ROUTES =====

@app.route('/api/admin/product-cards', methods=['GET'])
def get_product_cards():
    """Get all saved product cards"""
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, product_url, image_url, product_name, price, rating, created_at 
            FROM admin_product_cards 
            ORDER BY created_at DESC
        """)
        cards = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'cards': cards})
    except Exception as e:
        print(f"❌ Error fetching product cards: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/product-cards/add', methods=['POST'])
def add_product_card():
    """Save a new product card"""
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        product_url = data.get('product_url', '').strip()
        image_url = data.get('image_url', '').strip()
        product_name = data.get('product_name', '').strip()
        price = data.get('price', '').strip()
        rating = data.get('rating', '4.5').strip()
        
        if not all([product_url, image_url, product_name, price]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO admin_product_cards 
            (product_url, image_url, product_name, price, rating)
            VALUES (%s, %s, %s, %s, %s)
        """, (product_url, image_url, product_name, price, rating))
        
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        print(f"✅ Product card added with ID: {new_id}")
        return jsonify({'success': True, 'card_id': new_id})
        
    except Exception as e:
        print(f"❌ Error adding product card: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/product-cards/<int:card_id>', methods=['DELETE'])
def delete_product_card(card_id):
    """Delete a product card"""
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admin_product_cards WHERE id = %s", (card_id,))
        conn.commit()
        
        deleted_rows = cursor.rowcount
        cursor.close()
        conn.close()
        
        if deleted_rows > 0:
            print(f"✅ Deleted product card ID: {card_id}")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Card not found'}), 404
            
    except Exception as e:
        print(f"❌ Error deleting product card: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500    
    


@app.route('/api/admin/debug/products')
def debug_products():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SHOW TABLES LIKE 'products'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            return jsonify({'success': False, 'error': 'Products table does not exist'})
        
        cursor.execute("DESCRIBE products")
        columns = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) as count FROM products")
        count = cursor.fetchone()['count']
        
        cursor.execute("SELECT * FROM products LIMIT 5")
        products = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'table_exists': True,
            'columns': columns,
            'product_count': count,
            'sample_products': products
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400 
    
    
@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/')
def home():
    if 'user_email' in session:
        return render_template('index.html')
    else:
        return redirect('/login')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/home')
def home_page():
    if 'user_email' not in session:
        return redirect('/login')
    return render_template('index.html')

@app.route('/predict')
def predict_page():
    if 'user_email' not in session:
        return redirect('/login')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT platform FROM products ORDER BY platform")
        platforms = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return render_template('predict.html', categories=categories, platforms=platforms)
    except Exception as e:
        print(f"Error loading categories/platforms: {e}")
        return render_template('predict.html', categories=[], platforms=[])
    
@app.route('/contact')
def contact_page():
    return render_template('contact.html')

@app.route('/inquiry') 
def inquiry_page():
    return render_template('inquiry.html') 


@app.route('/shop-now')
def shop_now_page():
    """Public page showing all admin-added product cards"""
    return render_template('shop_now.html')


@app.route('/api/public/product-cards', methods=['GET'])
def get_public_product_cards():
    """Get all product cards for public display (no auth required)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, product_url, image_url, product_name, price, rating, created_at 
            FROM admin_product_cards 
            ORDER BY created_at DESC
        """)
        cards = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'cards': cards})
    except Exception as e:
        print(f"❌ Error fetching public product cards: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500 

@app.route('/api/contact', methods=['POST'])
def contact():
    try:
        data = request.json
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()
        
        # Validate inputs
        if not name or not email or not message:
            return jsonify({
                'success': False,
                'error': 'All fields are required'
            }), 400
        
        # Validate email format
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, email):
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400
        
        # TODO: Save to database or send email
        # For now, just log it
        print(f"\n📧 NEW CONTACT MESSAGE")
        print(f"Name: {name}")
        print(f"Email: {email}")
        print(f"Message: {message}")
        print("=" * 50)
        
        return jsonify({
            'success': True,
            'message': 'Thank you for contacting us! We will get back to you soon.'
        })
        
    except Exception as e:
        print(f"❌ Error in contact form: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        remember = data.get('remember', False)
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400
        
        # Check database for user
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        # Verify password: support legacy plaintext and modern hashed passwords
        verified = False
        if user:
            stored = user.get('password', '')
            try:
                # First try check_password_hash (supports werkzeug hashes)
                if stored and (':' in stored or stored.startswith('pbkdf2:')):
                    verified = check_password_hash(stored, password)
                else:
                    # Fallback to plain comparison for legacy records
                    verified = (stored == password)
            except Exception:
                # If hashing check fails for unknown format, fall back to plain compare
                verified = (stored == password)

        if user and verified:
            # If the stored password was plaintext (legacy), re-hash it and update the DB
            stored = user.get('password', '')
            try:
                is_plaintext = not (':' in stored or stored.startswith('pbkdf2:') or stored.startswith('scrypt:'))
            except Exception:
                is_plaintext = True

            if is_plaintext:
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    new_hash = generate_password_hash(password)
                    cur.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, user['id']))
                    conn.commit()
                    cur.close()
                    conn.close()
                    print(f"🔒 Migrated plaintext password to hashed for user: {email}")
                except Exception as e:
                    print(f"Warning: failed to migrate plaintext password for {email}: {e}")

            session.permanent = True
            session['user_email'] = email
            session['logged_in'] = True

            token = "demo_token_" + email
            print(f"✅ User logged in: {email}")
            return jsonify({
                'success': True,
                'token': token,
                'user': {'email': email}
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        if not name or not email or not password:
            return jsonify({
                'success': False,
                'error': 'All fields are required'
            }), 400
        
        # Check if user already exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Email already registered'
            }), 400
        
        # Hash password before storing
        hashed = generate_password_hash(password)

        # Insert new user
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        # Auto-login after signup
        session.permanent = True  # THIS IS THE NEW LINE
        session['user_email'] = email
        session['logged_in'] = True
        
        return jsonify({
            'success': True,
            'message': 'Account created successfully'
        })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/predict', methods=['POST'])
def predict():
    # Check if user is logged in
    if 'user_email' not in session:
        return jsonify({
            'success': False,
            'error': 'User not authenticated'
        }), 401
    
    print("\n" + "="*50)
    print("📮 NEW PREDICTION REQUEST")
    print("="*50)
    
    if not models_loaded:
        error_msg = 'Models not loaded. Please run model_training.py first.'
        print(f"❌ {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500
    
    try:
        data = request.json
        print(f"📥 Received data: {data}")
        
        # Extract user inputs
        category = data.get('category', 'Electronics')
        budget = float(data.get('budget', 5000))
        preferred_platform = data.get('platform', None)
        
        # Validate category
        if not category:
            raise ValueError("Category is required")
        
        # Encode category
        category_encoded = label_encoders['category'].transform([category])[0]
        
        # Calculate price range
        if budget < 1000:
            price_range = 0
        elif budget < 5000:
            price_range = 1
        elif budget < 15000:
            price_range = 2
        elif budget < 30000:
            price_range = 3
        else:
            price_range = 4
        
        # Default values
        rating_preference = 4.0
        stock_estimate = 200
        stock_status = 2
        
        # Rating category
        if rating_preference <= 3.5:
            rating_category = 0
        elif rating_preference <= 4.0:
            rating_category = 1
        elif rating_preference <= 4.5:
            rating_category = 2
        else:
            rating_category = 3
        
        # Predict best platform if not specified
        if preferred_platform:
            platform_encoded = label_encoders['platform'].transform([preferred_platform])[0]
            best_platform = preferred_platform
            platform_confidence = 100.0
        else:
            discount_estimate = 15
            discount_effectiveness = 0.15
            
            platform_features_vector = np.array([[
                category_encoded,
                budget,
                discount_estimate,
                rating_preference,
                stock_estimate,
                price_range,
                discount_effectiveness
            ]])
            
            platform_features_scaled = platform_scaler.transform(platform_features_vector)
            platform_encoded = platform_model.predict(platform_features_scaled)[0]
            platform_proba = platform_model.predict_proba(platform_features_scaled)[0]
            
            best_platform = label_encoders['platform'].inverse_transform([platform_encoded])[0]
            platform_confidence = float(platform_proba.max() * 100)
            
            print(f"🎯 Predicted Platform: {best_platform} ({platform_confidence:.1f}% confidence)")
        
        # Predict discount percentage
        stock_estimate = 200
        
        discount_features_vector = np.array([[
            platform_encoded,
            category_encoded,
            budget,
            rating_preference,
            stock_estimate,
            price_range,
            rating_category,
            stock_status
        ]])
        
        discount_features_scaled = discount_scaler.transform(discount_features_vector)
        predicted_discount = float(discount_model.predict(discount_features_scaled)[0])
        
        predicted_discount = max(0, min(50, predicted_discount))
        
        print(f"💰 Predicted Discount: {predicted_discount:.1f}%")
        
        # Calculate discounted price
        discounted_price = budget * (1 - predicted_discount / 100)
        savings = budget - discounted_price
        
        # Generate recommendations
        recommendations = generate_recommendations(
            predicted_discount, best_platform, category, budget
        )
        
        response = {
            'success': True,
            'predicted_discount': round(predicted_discount, 1),
            'best_platform': best_platform,
            'platform_confidence': round(platform_confidence, 1),
            'estimated_price': round(budget, 2),
            'discounted_price': round(discounted_price, 2),
            'savings': round(savings, 2),
            'category': category,
            'recommendations': recommendations,
            'model_used': model_metadata['discount_model_name'] if model_metadata else 'ML Model'
        }
        
        print(f"📤 Response: {response}")
        print("="*50 + "\n")
        
        # Save prediction to database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO predictions 
                (user_email, category, budget, platform, predicted_discount, 
                 predicted_platform, discounted_price, savings)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session.get('user_email', 'anonymous'),
                category,
                budget,
                data.get('platform', 'Auto'),
                predicted_discount,
                best_platform,
                discounted_price,
                savings
            ))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as db_error:
            print(f"Warning: Could not save prediction: {db_error}")
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error in prediction: {e}")
        import traceback
        traceback.print_exc()
        print("="*50 + "\n")
        return jsonify({'success': False, 'error': str(e)}), 400

def generate_recommendations(discount, platform, category, budget):
    """Generate shopping recommendations based on predictions"""
    recommendations = [] 
    
    if discount > 30:
        recommendations.append(f"🎉 Excellent! {platform} offers great discounts on {category}")
        recommendations.append(f"💡 You can save up to {discount:.0f}% - perfect time to buy!")
    elif discount > 20:
        recommendations.append(f"✅ Good deal! {platform} has decent discounts on {category}")
        recommendations.append(f"💰 Expected savings around {discount:.0f}%")
    else:
        recommendations.append(f"⚠️ Moderate discounts on {platform} for {category}")
        recommendations.append(f"💡 Consider waiting for sales or checking other platforms")
    
    if budget > 10000:
        recommendations.append("💳 High-value purchase - look for bank offers and EMI options")
    
    recommendations.append(f"📊 Compare prices across platforms before purchasing")
    recommendations.append(f"⭐ Check product ratings and reviews")
    
    return recommendations



@app.route('/api/categories')
def get_categories():
    """Get all available categories"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'categories': categories})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/platforms')
def get_platforms():
    """Get all available platforms"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT platform FROM products ORDER BY platform")
        platforms = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'platforms': platforms})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ===== IMPROVED SEARCH ROUTE =====
# Replace your existing /api/search route with this improved version

@app.route('/api/search', methods=['POST'])
def search_products():
    """🎯 Multi-platform product search and comparison - NO IMAGES"""
    if 'user_email' not in session:
        return jsonify({
            'success': False,
            'error': 'User not authenticated'
        }), 401

    try:
        from api_integrations import MultiPlatformAPIIntegration
        
        data = request.json
        product_name = data.get('product_name', '').strip()
        max_price = float(data.get('max_price')) if data.get('max_price') else None
        sort_by = data.get('sort_by', 'price')

        if not product_name:
            return jsonify({
                'success': False,
                'error': 'Product name is required'
            }), 400

        print(f"\n{'='*70}")
        print(f"🔍 MULTI-PLATFORM SEARCH REQUEST")
        print(f"{'='*70}")
        print(f"User: {session.get('user_email')}")
        print(f"Query: {product_name}")
        print(f"Max Price: ₹{max_price:,.0f}" if max_price else "Max Price: No limit")
        print(f"Sort By: {sort_by}")
        print(f"{'='*70}\n")

        # Initialize multi-platform API
        api = MultiPlatformAPIIntegration()

        # Compare products across platforms
        comparison_result = api.compare_products(
            query=product_name,
            max_price=max_price
        )

        all_products = comparison_result['products']

        # Enhanced product filtering with fuzzy matching
        if all_products:
            try:
                tokens = [t.lower() for t in product_name.split() if len(t) >= 2]
            except Exception:
                tokens = []

            STOPWORDS = {'laptop', 'laptops', 'notebook', 'pc', 'computer', 'computers', 
                        'mobile', 'phone', 'device', 'watch', 'watches', 'shoe', 'shoes',
                        'headphone', 'headphones', 'earphone', 'earphones'}
            tokens = [t for t in tokens if t not in STOPWORDS]

            if tokens:
                import math
                import difflib

                def token_matches_in_text(tok: str, text: str) -> bool:
                    if not tok or not text:
                        return False
                    if tok in text:
                        return True
                    ratio = difflib.SequenceMatcher(None, tok, text).ratio()
                    return ratio >= 0.72

                def score_product(product: dict) -> int:
                    name = (product.get('product_name') or '').lower()
                    platform = (product.get('platform') or '').lower()
                    category = (product.get('category') or '').lower()
                    match_count = 0
                    for tok in tokens:
                        if token_matches_in_text(tok, name):
                            match_count += 2  # Name matches count double
                        elif token_matches_in_text(tok, platform):
                            match_count += 1
                        elif token_matches_in_text(tok, category):
                            match_count += 1
                    return match_count

                min_required = max(1, math.ceil(len(tokens) * 0.4))
                scored = [(p, score_product(p)) for p in all_products]
                filtered = [p for p, s in scored if s >= min_required]

                if filtered:
                    print(f"🔎 Filtered to {len(filtered)}/{len(all_products)} relevant products")
                    all_products = filtered
                else:
                    softer = [p for p, s in scored if s >= 1]
                    if softer:
                        print(f"🔎 Using softer match: {len(softer)} products")
                        all_products = softer

        # Sort products
        if sort_by == 'discount':
            all_products.sort(key=lambda x: x['discount_percent'], reverse=True)
        else:  # sort by price
            all_products.sort(key=lambda x: x['discounted_price'])

        # Format products for frontend - NO IMAGES
        formatted_products = []
        for product in all_products:
            formatted_products.append({
                'name': product['product_name'],
                'mrp': product['price'],
                'sale_price': product['discounted_price'],
                'discount': product['discount_percent'],
                'product_link': product.get('product_url', '#'),
                'platform': product['platform'],
                'rating': product['rating'],
                'savings': product.get('savings', product['price'] - product['discounted_price'])
            })

        # Prepare response
        response = {
            'success': True,
            'products': formatted_products,
            'total_count': comparison_result['total_count'],
            'amazon_count': comparison_result['amazon_count'],
            'flipkart_count': comparison_result['flipkart_count']
        }

        # Add best deal info
        # Add best deal info with safe defaults
        if comparison_result.get('best_deal'):
            best = comparison_result['best_deal']
            response['best_deal'] = {
                'name': best.get('product_name', 'Unknown Product'),
                'mrp': best.get('price', 0),
                'sale_price': best.get('discounted_price', 0),
                'discount': best.get('discount_percent', 0),
                'platform': best.get('platform', 'Unknown'),
                'image_url': best.get('image_url', 'https://via.placeholder.com/300x200?text=Product'),
                'product_link': best.get('product_url', '#'),
                'rating': best.get('rating', 0)
            }
        else:
            # Provide fallback if no best deal found
            if formatted_products:
                first_product = all_products[0]
                response['best_deal'] = {
                    'name': first_product.get('product_name', 'Product'),
                    'mrp': first_product.get('price', 0),
                    'sale_price': first_product.get('discounted_price', 0),
                    'discount': first_product.get('discount_percent', 0),
                    'platform': first_product.get('platform', 'Platform'),
                    'image_url': first_product.get('image_url', 'https://via.placeholder.com/300x200?text=Product'),
                    'product_link': first_product.get('product_url', '#'),
                    'rating': first_product.get('rating', 0)
                } 

        # Add highest discount info
        if comparison_result.get('highest_discount'):
            highest = comparison_result['highest_discount']
            response['highest_discount_product'] = {
                'name': highest['product_name'],
                'mrp': highest['price'],
                'sale_price': highest['discounted_price'],
                'discount': highest['discount_percent'],
                'platform': highest['platform'],
                'product_link': highest.get('product_url', '#')
            }

        # Add platform statistics
        response['platform_stats'] = comparison_result.get('platform_stats', {})
        response['best_platform'] = comparison_result.get('best_platform')

        print(f"\n✅ SEARCH COMPLETE")
        print(f"   Total Products: {len(formatted_products)}")
        print(f"   Best Deal Platform: {comparison_result.get('best_deal', {}).get('platform', 'N/A')}")
        print(f"   Overall Best Platform: {comparison_result.get('best_platform', 'N/A')}")
        print(f"{'='*70}\n")

        return jsonify(response)

    except Exception as e:
        print(f"❌ Error in product search: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  