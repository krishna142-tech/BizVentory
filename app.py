from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
import os
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime, timedelta
import socket
import netifaces
import json
import csv
from io import StringIO
from collections import defaultdict
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data
        self.id = str(user_data['_id'])
        self.email = user_data.get('email')
        self.username = user_data.get('username')
        self.business_id = str(user_data['business_id']) if 'business_id' in user_data else None

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if user_data:
            return User(user_data)
    except Exception as e:
        print(f"Error loading user: {str(e)}")
    return None

# Add context processor for datetime and cart count
@app.context_processor
def inject_globals():
    cart_count = len(session.get('cart', {})) if 'user_id' in session else 0
    return {
        'now': datetime.utcnow(),
        'cart_count': cart_count
    }

# MongoDB configuration
app.config["MONGO_URI"] = os.getenv('MONGO_URI', 'mongodb://localhost:27017/bizventory')
mongo = PyMongo(app)

# SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///app.db')
db = SQLAlchemy(app)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_data = mongo.db.users.find_one({'email': email})
        
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            session['user_id'] = str(user_data['_id'])
            
            # Get business info and store business name in session
            if 'business_id' in user_data:
                business = mongo.db.businesses.find_one({'_id': user_data['business_id']})
                if business:
                    session['business_name'] = business['name']
                    session['business_id'] = str(business['_id'])
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'redirect': url_for('dashboard')
                })
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            })
        
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Store business information in session
        session['business_info'] = {
            'business_name': request.form.get('business_name'),
            'business_type': request.form.get('business_type'),
            'business_description': request.form.get('business_description'),
            'owner_name': request.form.get('owner_name'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'alternate_email': request.form.get('alternate_email'),
            'address': request.form.get('address'),
            'currency': request.form.get('currency', 'USD')  # Add currency with USD as default
        }
        return redirect(url_for('account_setup'))
    return render_template('register.html')

@app.route('/account_setup', methods=['GET'])
def account_setup():
    # Check if business info exists in session
    if 'business_info' not in session:
        flash('Please complete business registration first', 'error')
        return redirect(url_for('register'))
    return render_template('account_setup.html')

@app.route('/create_account', methods=['POST'])
def create_account():
    if 'business_info' not in session:
        flash('Please complete business registration first', 'error')
        return redirect(url_for('register'))

    # Get business info from session
    business_info = session['business_info']
    
    # Get account info from form
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    tax_id = request.form.get('tax_id')

    # Validate input
    if not username or not password or not confirm_password:
        flash('All required fields must be filled', 'error')
        return redirect(url_for('account_setup'))

    # Validate username format
    if not re.match(r'^[a-zA-Z0-9_-]{3,30}$', username):
        flash('Username must be 3-30 characters long and can only contain letters, numbers, underscores, and hyphens', 'error')
        return redirect(url_for('account_setup'))

    # Check if username already exists
    if mongo.db.users.find_one({'username': username}):
        flash('Username already exists', 'error')
        return redirect(url_for('account_setup'))

    # Validate password
    if len(password) < 8:
        flash('Password must be at least 8 characters long', 'error')
        return redirect(url_for('account_setup'))

    if password != confirm_password:
        flash('Passwords do not match', 'error')
        return redirect(url_for('account_setup'))

    try:
        # Create business document
        business_doc = {
            'name': business_info['business_name'],
            'type': business_info['business_type'],
            'description': business_info['business_description'],
            'owner_name': business_info['owner_name'],
            'phone': business_info['phone'],
            'email': business_info['email'],
            'alternate_email': business_info['alternate_email'],
            'address': business_info['address'],
            'currency': business_info.get('currency', 'USD'),
            'tax_id': tax_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert business record
        business_result = mongo.db.businesses.insert_one(business_doc)
        
        # Create user document
        user_doc = {
            'username': username,
            'password': generate_password_hash(password),
            'business_id': business_result.inserted_id,
            'email': business_info['email'],
            'role': 'owner',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'last_login': None
        }
        
        # Insert user record
        user_result = mongo.db.users.insert_one(user_doc)
        
        # Clear session
        session.pop('business_info', None)
        
        # Log the user in
        user = User(user_doc)
        login_user(user)
        
        flash('Account created successfully! Welcome to BizVentory.', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        # If there's an error, try to clean up any created records
        if 'business_result' in locals():
            mongo.db.businesses.delete_one({'_id': business_result.inserted_id})
        flash('An error occurred while creating your account. Please try again.', 'error')
        return redirect(url_for('account_setup'))

def get_currency_symbol():
    """Get the user's currency symbol from settings"""
    if 'user_id' not in session:
        return '$'  # Default currency symbol
    
    settings = mongo.db.business_settings.find_one({'user_id': ObjectId(session['user_id'])})
    if not settings:
        return '$'
    
    currency_code = settings.get('inventory_settings', {}).get('currency', 'USD')
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'INR': '₹',
        'CNY': '¥',
        'AUD': 'A$',
        'CAD': 'C$',
        'CHF': 'Fr',
        'HKD': 'HK$'
    }
    return currency_symbols.get(currency_code, '$')

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    user_id = ObjectId(session['user_id'])
    
    # Get inventory items
    inventory_items = list(mongo.db.inventory.find({'user_id': user_id}))
    
    # Calculate basic stats
    total_items = len(inventory_items)
    total_value = sum(item['quantity'] * item['price'] for item in inventory_items)
    low_stock_items = sum(1 for item in inventory_items if item.get('is_low_stock', False))
    
    # Get unique categories and brands
    categories = sorted(list(set(item['category'] for item in inventory_items if 'category' in item)))
    brands = sorted(list(set(item['brand'] for item in inventory_items if 'brand' in item)))
    
    # Calculate additional metrics
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    # Get transactions for the last 30 days
    transactions = list(mongo.db.transactions.find({
        'user_id': user_id,
        'created_at': {'$gte': start_date, '$lte': end_date}
    }).sort('created_at', 1))
    
    # Initialize daily metrics
    daily_data = {}
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.strftime('%Y-%m-%d')
        daily_data[date_key] = {
            'revenue': 0,
            'profit': 0,
            'transactions': 0,
            'items_sold': 0
        }
        current_date += timedelta(days=1)
    
    # Calculate daily metrics
    total_revenue = 0
    total_profit = 0
    total_transactions = 0
    total_items_sold = 0
    
    for transaction in transactions:
        date_key = transaction['created_at'].strftime('%Y-%m-%d')
        revenue = transaction['total_amount']
        # Calculate actual profit based on items' purchase prices
        profit = sum((item.get('price', 0) - item.get('purchase_price', 0)) * item.get('quantity', 0) 
                    for item in transaction['items'])
        items_sold = sum(item.get('quantity', 0) for item in transaction['items'])
        
        daily_data[date_key]['revenue'] += revenue
        daily_data[date_key]['profit'] += profit
        daily_data[date_key]['transactions'] += 1
        daily_data[date_key]['items_sold'] += items_sold
        
        total_revenue += revenue
        total_profit += profit
        total_transactions += 1
        total_items_sold += items_sold
    
    # Calculate averages and trends
    avg_daily_revenue = total_revenue / 30 if total_revenue > 0 else 0
    avg_daily_profit = total_profit / 30 if total_profit > 0 else 0
    avg_transaction_value = total_revenue / total_transactions if total_transactions > 0 else 0
    
    # Calculate stock efficiency
    total_stock = sum(item['quantity'] for item in inventory_items)
    stock_efficiency = (total_items_sold / total_stock * 100) if total_stock > 0 else 0
    
    # Calculate revenue growth (compare with previous period)
    prev_start_date = start_date - timedelta(days=30)
    prev_transactions = list(mongo.db.transactions.find({
        'user_id': user_id,
        'created_at': {'$gte': prev_start_date, '$lt': start_date}
    }))
    prev_revenue = sum(t['total_amount'] for t in prev_transactions)
    revenue_growth = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    
    # Prepare predictions data
    future_dates = [(end_date + timedelta(days=x)).strftime('%Y-%m-%d') for x in range(1, 31)]
    
    # Simple linear regression for predictions
    dates_numeric = list(range(len(daily_data)))
    revenues = [data['revenue'] for data in daily_data.values()]
    profits = [data['profit'] for data in daily_data.values()]
    
    if len(dates_numeric) > 1:  # Need at least 2 points for regression
        revenue_slope, revenue_intercept = np.polyfit(dates_numeric, revenues, 1)
        profit_slope, profit_intercept = np.polyfit(dates_numeric, profits, 1)
        
        future_revenues = [revenue_slope * (i + len(dates_numeric)) + revenue_intercept for i in range(30)]
        future_profits = [profit_slope * (i + len(dates_numeric)) + profit_intercept for i in range(30)]
    else:
        # Fallback if not enough data
        future_revenues = [avg_daily_revenue] * 30
        future_profits = [avg_daily_profit] * 30

    predictions = [
        {
            'date': date,
            'predicted_revenue': max(0, revenue),  # Ensure non-negative values
            'predicted_profit': max(0, profit)
        }
        for date, revenue, profit in zip(future_dates, future_revenues, future_profits)
    ]

    # Prepare visualization data
    visualization_data = {
        'kpis': {
            'gross_profit_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
            'inventory_turnover': total_transactions / 30 if total_transactions > 0 else 0,  # Daily average
            'return_on_investment': (total_profit / total_value * 100) if total_value > 0 else 0,
            'average_transaction_value': avg_transaction_value
        },
        'daily_sales': [
            {
                'date': date,
                'revenue': data['revenue'],
                'profit': data['profit'],
                'revenue_ma': calculate_moving_average([d['revenue'] for d in list(daily_data.values())], 7, i),
                'profit_ma': calculate_moving_average([d['profit'] for d in list(daily_data.values())], 7, i)
            }
            for i, (date, data) in enumerate(daily_data.items())
        ],
        'category_performance': [
            {
                'category': category,
                'revenue': sum(item['price'] * item['quantity'] for item in inventory_items if item['category'] == category),
                'profit_margin': calculate_category_profit_margin(inventory_items, category),
                'units': sum(item['quantity'] for item in inventory_items if item['category'] == category)
            }
            for category in categories
        ],
        'additional_metrics': {
            'cash_flow': total_revenue - sum(item.get('cost_price', 0) * item.get('quantity', 0) for item in inventory_items),
            'operating_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
            'stock_efficiency': stock_efficiency,
            'revenue_growth': revenue_growth
        },
        'predictions': predictions,  # Add predictions to visualization data
        'trends': {
            'dates': list(daily_data.keys()),
            'profit_margin': [data['profit'] / data['revenue'] * 100 if data['revenue'] > 0 else 0 for data in daily_data.values()],
            'inventory_turnover': [data['transactions'] for data in daily_data.values()],
            'roi': [(data['profit'] / total_value * 100) if total_value > 0 else 0 for data in daily_data.values()],
            'avg_transaction': [data['revenue'] / data['transactions'] if data['transactions'] > 0 else 0 for data in daily_data.values()]
        }
    }

    return render_template('dashboard.html',
        inventory_items=inventory_items,
        total_items=total_items,
        total_value=total_value,
        low_stock_items=low_stock_items,
        total_categories=len(categories),
        all_categories=categories,
        all_brands=brands,
        currency=get_currency_symbol(),
        visualization_data=visualization_data
    )

def calculate_moving_average(data, window, index):
    """Calculate moving average for a specific index in the data"""
    start = max(0, index - window + 1)
    window_data = data[start:index + 1]
    return sum(window_data) / len(window_data)

def calculate_category_profit_margin(items, category):
    """Calculate profit margin for a category"""
    category_items = [item for item in items if item['category'] == category]
    total_revenue = sum(item['price'] * item['quantity'] for item in category_items)
    total_cost = sum(item.get('cost_price', 0) * item['quantity'] for item in category_items)
    return ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0

@app.route('/add_item', methods=['POST'])
@login_required
def add_item():
    try:
        data = request.form
        brand = data.get('brand')
        category = data.get('category')
        
        # Handle new brand
        if brand == 'new':
            brand = data.get('newBrand')
        
        # Handle new category
        if category == 'new':
            category = data.get('newCategory')
        
        # If brand is provided but category is not, get the first category for this brand
        if brand and not category:
            brand_item = mongo.db.inventory.find_one({
                'user_id': ObjectId(session['user_id']),
                'brand': brand
            })
            if brand_item:
                category = brand_item.get('category')
        
        # Validate required fields
        if not data.get('name'):
            flash('Item name is required', 'error')
            return redirect(url_for('inventory'))
        
        try:
            quantity = int(data.get('quantity', 0))
            price = float(data.get('price', 0))
            purchase_price = float(data.get('purchase_price', 0))
            min_quantity = int(data.get('min_quantity', 0))
        except ValueError:
            flash('Invalid quantity or price values', 'error')
            return redirect(url_for('inventory'))
        
        if quantity < 0 or price < 0 or purchase_price < 0 or min_quantity < 0:
            flash('Quantity and prices must be positive numbers', 'error')
            return redirect(url_for('inventory'))
        
        item = {
            'user_id': ObjectId(session['user_id']),
            'name': data.get('name'),
            'brand': brand,
            'category': category,
            'quantity': quantity,
            'price': price,
            'purchase_price': purchase_price,
            'min_quantity': min_quantity,
            'created_at': datetime.utcnow()
        }
        
        result = mongo.db.inventory.insert_one(item)
        
        if result.inserted_id:
            flash('Item added successfully!', 'success')
        else:
            flash('Failed to add item', 'error')
            
        return redirect(url_for('inventory', brand=brand, category=category))
        
    except Exception as e:
        print(f"Error adding item: {str(e)}")  # Log the error
        flash('An error occurred while adding the item. Please try again.', 'error')
        return redirect(url_for('inventory'))

@app.route('/edit_item/<item_id>', methods=['POST'])
@login_required
def edit_item(item_id):
    try:
        # Get form data
        name = request.form.get('name')
        brand = request.form.get('brand')
        category = request.form.get('category')
        quantity = int(request.form.get('quantity'))
        price = float(request.form.get('price'))
        purchase_price = float(request.form.get('purchase_price'))
        min_quantity = int(request.form.get('min_quantity'))

        # Update the item in the database, ensuring it belongs to the current user
        result = mongo.db.inventory.update_one(
            {
                '_id': ObjectId(item_id),
                'user_id': ObjectId(session['user_id'])
            },
            {
                '$set': {
                    'name': name,
                    'brand': brand,
                    'category': category,
                    'quantity': quantity,
                    'price': price,
                    'purchase_price': purchase_price,
                    'min_quantity': min_quantity,
                    'updated_at': datetime.utcnow()
                }
            }
        )

        if result.matched_count == 0:
            flash('Item not found or you do not have permission to edit it.', 'error')
        elif result.modified_count > 0:
            flash('Item updated successfully!', 'success')
        else:
            flash('No changes were made to the item.', 'info')
        
        return redirect(url_for('inventory'))
    except ValueError as e:
        flash('Invalid input values. Please check your input and try again.', 'error')
        return redirect(url_for('inventory'))
    except Exception as e:
        print(f"Error updating item: {str(e)}")  # Log the error
        flash('An error occurred while updating the item. Please try again.', 'error')
        return redirect(url_for('inventory'))

@app.route('/delete_item/<item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    mongo.db.inventory.delete_one({
        '_id': ObjectId(item_id),
        'user_id': ObjectId(session['user_id'])
    })
    
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/inventory')
@login_required
def inventory():
    # Get filter parameters
    category = request.args.get('category')
    brand = request.args.get('brand')
    
    # Build query
    query = {'user_id': ObjectId(session['user_id'])}
    if category:
        query['category'] = category
    if brand:
        query['brand'] = brand

    # Get items with filters
    inventory_items = list(mongo.db.inventory.find(query))
    
    # Add is_low_stock flag to items
    for item in inventory_items:
        item['is_low_stock'] = item['quantity'] <= item['min_quantity']
    
    # Get all unique categories and brands
    all_categories = mongo.db.inventory.distinct('category', {'user_id': ObjectId(session['user_id'])})
    all_brands = mongo.db.inventory.distinct('brand', {'user_id': ObjectId(session['user_id'])})
    
    # Get brand categories mapping
    brand_categories = {}
    if brand:
        brand_items = mongo.db.inventory.find({'user_id': ObjectId(session['user_id']), 'brand': brand})
        brand_categories[brand] = list(set(item['category'] for item in brand_items))
    else:
        # Get categories for all brands
        for b in all_brands:
            brand_items = mongo.db.inventory.find({'user_id': ObjectId(session['user_id']), 'brand': b})
            brand_categories[b] = list(set(item['category'] for item in brand_items))
    
    # Get user's currency setting
    settings = mongo.db.business_settings.find_one({'user_id': ObjectId(session['user_id'])})
    currency = settings.get('inventory_settings', {}).get('currency', 'USD') if settings else 'USD'
    
    return render_template('inventory.html',
        inventory_items=inventory_items,
        all_categories=all_categories,
        all_brands=all_brands,
        selected_category=category,
        selected_brand=brand,
        brand_categories=brand_categories,
        currency=currency
    )

@app.route('/settings')
@login_required
def settings():
    user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    settings = mongo.db.business_settings.find_one({'user_id': ObjectId(session['user_id'])})
    
    # Initialize default settings if they don't exist
    if not settings:
        default_settings = {
            'user_id': ObjectId(session['user_id']),
            'notification_preferences': {
                'low_stock_alerts': True,
                'daily_reports': False,
                'email_notifications': True
            },
            'inventory_settings': {
                'default_low_stock_threshold': 10,
                'currency': 'USD',
                'date_format': 'MM/DD/YYYY'
            }
        }
        mongo.db.business_settings.insert_one(default_settings)
        settings = default_settings
    
    return render_template('settings.html', user=user, settings=settings)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.form
    updates = {
        'business_name': data.get('business_name'),
        'business_type': data.get('business_type'),
        'email': data.get('email')
    }
    
    mongo.db.users.update_one(
        {'_id': ObjectId(session['user_id'])},
        {'$set': updates}
    )
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    data = request.form
    notification_updates = {
        'notification_preferences.low_stock_alerts': 'low_stock_alerts' in data,
        'notification_preferences.daily_reports': 'daily_reports' in data,
        'notification_preferences.email_notifications': 'email_notifications' in data
    }
    
    inventory_updates = {}
    if 'low_stock_threshold' in data:
        inventory_updates['inventory_settings.default_low_stock_threshold'] = int(data.get('low_stock_threshold'))
    if 'currency' in data:
        inventory_updates['inventory_settings.currency'] = data.get('currency')
    if 'date_format' in data:
        inventory_updates['inventory_settings.date_format'] = data.get('date_format')
    
    updates = {**notification_updates, **inventory_updates}
    
    mongo.db.business_settings.update_one(
        {'user_id': ObjectId(session['user_id'])},
        {'$set': updates}
    )
    
    flash('Settings updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/get_item/<item_id>')
@login_required
def get_item(item_id):
    try:
        # Find item that belongs to the current user
        item = mongo.db.inventory.find_one({
            '_id': ObjectId(item_id),
            'user_id': ObjectId(session['user_id'])
        })
        
        if item:
            # Convert ObjectId to string for JSON serialization
            item['_id'] = str(item['_id'])
            item['user_id'] = str(item['user_id'])
            return jsonify(item)
        return jsonify({'error': 'Item not found'}), 404
    except Exception as e:
        print(f"Error getting item: {str(e)}")  # Log the error
        return jsonify({'error': 'Failed to load item details'}), 500

@app.route('/transaction_history')
@login_required
def transaction_history():
    # Get all transactions for the user
    transactions = list(mongo.db.transactions.find(
        {'user_id': ObjectId(session['user_id'])}
    ).sort('created_at', -1))  # Sort by newest first
    
    # Get user's currency setting
    settings = mongo.db.business_settings.find_one({'user_id': ObjectId(session['user_id'])})
    currency = settings.get('inventory_settings', {}).get('currency', 'USD') if settings else 'USD'
    
    return render_template(
        'transaction_history.html',
        transactions=transactions,
        currency=currency
    )

@app.route('/reports')
@login_required
def reports():
    try:
        period = request.args.get('period', 'daily')
        
        # Get date range based on period
        end_date = datetime.now()
        if period == 'daily':
            start_date = end_date - timedelta(days=1)
            date_format = '%H:%M'
            period_text = "Daily Report (Last 24 Hours)"
        elif period == 'weekly':
            start_date = end_date - timedelta(weeks=1)
            date_format = '%a'
            period_text = "Weekly Report (Last 7 Days)"
        elif period == 'monthly':
            start_date = end_date - timedelta(days=30)
            date_format = '%d %b'
            period_text = "Monthly Report (Last 30 Days)"
        else:  # yearly
            start_date = end_date - timedelta(days=365)
            date_format = '%b'
            period_text = "Yearly Report (Last 365 Days)"

        # Initialize default values
        total_sales = 0
        total_orders = 0
        sales_trend = 0
        order_trend = 0
        dates = []
        sales_amounts = []
        category_data = {}
        brand_data = {}

        # Get user's currency setting
        settings = mongo.db.business_settings.find_one({'user_id': ObjectId(session['user_id'])})
        currency = settings.get('inventory_settings', {}).get('currency', '$') if settings else '$'

        # Get transactions for the period
        transactions = list(mongo.db.transactions.find({
            'user_id': ObjectId(session['user_id']),
            'created_at': {'$gte': start_date, '$lte': end_date}
        }).sort('created_at', 1))

        if transactions:
            # Calculate total sales and orders
            total_sales = sum(t['total_amount'] for t in transactions)
            total_orders = len(transactions)

            # Group sales by date
            sales_by_date = defaultdict(float)
            for t in transactions:
                date_key = t['created_at'].strftime(date_format)
                sales_by_date[date_key] += t['total_amount']

            # Prepare chart data
            dates = sorted(sales_by_date.keys())
            sales_amounts = [sales_by_date[date] for date in dates]

            # Calculate trends
            prev_start = start_date - (end_date - start_date)
            prev_transactions = list(mongo.db.transactions.find({
                'user_id': ObjectId(session['user_id']),
                'created_at': {'$gte': prev_start, '$lt': start_date}
            }))

            if prev_transactions:
                prev_sales = sum(t['total_amount'] for t in prev_transactions)
                prev_orders = len(prev_transactions)
                
                if prev_sales > 0:
                    sales_trend = ((total_sales - prev_sales) / prev_sales) * 100
                if prev_orders > 0:
                    order_trend = ((total_orders - prev_orders) / prev_orders) * 100

            # Get category and brand distribution
            for t in transactions:
                for item in t['items']:
                    # Get the actual item from inventory to get its current category and brand
                    inventory_item = mongo.db.inventory.find_one({'_id': ObjectId(item['item_id'])})
                    if inventory_item:
                        # Process category data
                        category = inventory_item.get('category', 'Uncategorized')
                        if category not in category_data:
                            category_data[category] = {
                                'sales': 0,
                                'items': 0
                            }
                        category_data[category]['sales'] += item['total']
                        category_data[category]['items'] += item['quantity']

                        # Process brand data
                        brand = inventory_item.get('brand', 'Unbranded')
                        if brand not in brand_data:
                            brand_data[brand] = {
                                'sales': 0,
                                'items': 0,
                                'categories': set()
                            }
                        brand_data[brand]['sales'] += item['total']
                        brand_data[brand]['items'] += item['quantity']
                        brand_data[brand]['categories'].add(category)

        # Sort categories by sales and get top 5
        sorted_categories = sorted(category_data.items(), key=lambda x: x[1]['sales'], reverse=True)[:5]
        category_labels = [cat[0] for cat in sorted_categories]
        category_values = [cat[1]['sales'] for cat in sorted_categories]

        # Sort brands by sales and get top 5
        sorted_brands = sorted(brand_data.items(), key=lambda x: x[1]['sales'], reverse=True)[:5]
        brand_labels = [brand[0] for brand in sorted_brands]
        brand_values = [brand[1]['sales'] for brand in sorted_brands]
        brand_categories = {brand[0]: list(brand[1]['categories']) for brand in sorted_brands}

        # Calculate average order value
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0

        return render_template('reports.html',
            currency=currency,
            period=period,
            period_text=period_text,
            total_sales=total_sales,
            total_orders=total_orders,
            avg_order_value=avg_order_value,
            sales_trend=sales_trend,
            order_trend=order_trend,
            dates=dates,
            sales_data=sales_amounts,
            category_labels=category_labels,
            category_data=category_values,
            brand_labels=brand_labels,
            brand_data=brand_values,
            brand_categories=brand_categories
        )

    except Exception as e:
        print(f"Error generating report: {str(e)}")  # Log the error
        flash('An error occurred while generating the report. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/download_report')
@login_required
def download_report():
    period = request.args.get('period', 'daily')
    business_id = session.get('business_id')
    
    # Similar date range logic as reports route
    end_date = datetime.now()
    if period == 'daily':
        start_date = end_date - timedelta(days=1)
    elif period == 'weekly':
        start_date = end_date - timedelta(weeks=1)
    elif period == 'monthly':
        start_date = end_date - timedelta(days=30)
    else:
        start_date = end_date - timedelta(days=365)

    # Query for report data
    report_query = """
        SELECT 
            o.created_at,
            o.id as order_id,
            o.total_amount,
            o.status,
            STRING_AGG(CONCAT(oi.quantity, 'x ', i.name), ', ') as items
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN items i ON oi.item_id = i.id
        WHERE o.business_id = :business_id
        AND o.created_at BETWEEN :start_date AND :end_date
        GROUP BY o.id, o.created_at, o.total_amount, o.status
        ORDER BY o.created_at DESC
    """
    
    orders = db.session.execute(text(report_query), {
        'business_id': business_id,
        'start_date': start_date,
        'end_date': end_date
    }).fetchall()

    # Create CSV file
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Order ID', 'Items', 'Total Amount', 'Status'])
    
    for order in orders:
        writer.writerow([
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.order_id,
            order.items,
            float(order.total_amount),
            order.status
        ])

    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=sales_report_{period}_{datetime.now().strftime("%Y%m%d")}.csv'
        }
    )

@app.route('/shop')
def shop():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get filter parameters
    categories = request.args.get('categories', '').split(',') if request.args.get('categories') else []
    min_price = float(request.args.get('min_price')) if request.args.get('min_price') else None
    max_price = float(request.args.get('max_price')) if request.args.get('max_price') else None
    in_stock_only = bool(request.args.get('in_stock'))
    sort_by = request.args.get('sort', 'name')
    
    # Build query
    query = {'user_id': ObjectId(session['user_id'])}
    if categories:
        query['category'] = {'$in': categories}
    if min_price is not None:
        query['price'] = {'$gte': min_price}
    if max_price is not None:
        query.setdefault('price', {})['$lte'] = max_price
    if in_stock_only:
        query['quantity'] = {'$gt': 0}
    
    # Get sort parameters
    sort_params = [('name', 1)]  # Default sort
    if sort_by == 'price_asc':
        sort_params = [('price', 1)]
    elif sort_by == 'price_desc':
        sort_params = [('price', -1)]
    
    # Get items
    items = list(mongo.db.inventory.find(query).sort(sort_params))
    
    # Get all unique categories
    all_categories = mongo.db.inventory.distinct('category', {'user_id': ObjectId(session['user_id'])})
    
    # Get user's currency setting
    settings = mongo.db.business_settings.find_one({'user_id': ObjectId(session['user_id'])})
    currency = settings.get('inventory_settings', {}).get('currency', 'USD') if settings else 'USD'
    
    return render_template('shop.html',
        items=items,
        categories=all_categories,
        selected_categories=categories,
        min_price=min_price,
        max_price=max_price,
        in_stock_only=in_stock_only,
        sort_by=sort_by,
        currency=currency
    )

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Initialize cart in session if it doesn't exist
    if 'cart' not in session:
        session['cart'] = {}
    
    cart_items = []
    subtotal = 0
    total_items = 0
    
    # Get user's currency setting
    settings = mongo.db.business_settings.find_one({'user_id': ObjectId(session['user_id'])})
    currency = settings.get('inventory_settings', {}).get('currency', 'USD') if settings else 'USD'
    
    # Get cart items with current inventory data
    for item_id, quantity in session['cart'].items():
        try:
            inventory_item = mongo.db.inventory.find_one({
                '_id': ObjectId(item_id),
                'user_id': ObjectId(session['user_id'])
            })
            
            if inventory_item and inventory_item['quantity'] > 0:
                item_total = quantity * inventory_item['price']
                subtotal += item_total
                total_items += quantity
                
                cart_items.append({
                    '_id': str(inventory_item['_id']),
                    'name': inventory_item['name'],
                    'category': inventory_item['category'],
                    'price': inventory_item['price'],
                    'quantity': inventory_item['quantity'],
                    'cart_quantity': quantity,
                    'total': item_total
                })
        except Exception as e:
            print(f"Error processing cart item {item_id}: {str(e)}")
    
    total = subtotal  # Add tax calculation here if needed
    
    return render_template('cart.html',
        cart_items=cart_items,
        subtotal=subtotal,
        total=total,
        total_items=total_items,
        currency=currency
    )

@app.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400
        
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        
        if not item_id or quantity < 1:
            return jsonify({'success': False, 'error': 'Invalid item ID or quantity'}), 400
        
        # Get item from inventory
        item = mongo.db.inventory.find_one({
            '_id': ObjectId(item_id),
            'user_id': ObjectId(session['user_id'])  # Changed from business_id to user_id
        })
        
        if not item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404
        
        if quantity > item.get('quantity', 0):
            return jsonify({'success': False, 'error': 'Not enough stock available'}), 400
        
        # Initialize cart if it doesn't exist
        if 'cart' not in session:
            session['cart'] = {}
        
        # Update cart
        cart = session['cart']
        if item_id in cart:
            cart[item_id] += quantity
        else:
            cart[item_id] = quantity
        
        # Check if total quantity exceeds available stock
        if cart[item_id] > item.get('quantity', 0):
            cart[item_id] = item['quantity']
        
        session.modified = True
        
        return jsonify({
            'success': True,
            'cart_count': sum(cart.values()),  # Changed to sum of quantities
            'message': 'Item added to cart successfully'
        })
        
    except Exception as e:
        print(f"Error adding to cart: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while adding item to cart'}), 500

@app.route('/cart/update', methods=['POST'])
def update_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400
        
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 0))
        
        if not item_id or quantity < 0:
            return jsonify({'success': False, 'error': 'Invalid item ID or quantity'}), 400
        
        # Get item from inventory
        item = mongo.db.inventory.find_one({
            '_id': ObjectId(item_id),
            'user_id': ObjectId(session['user_id'])
        })
        
        if not item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404
        
        if quantity > item['quantity']:
            return jsonify({'success': False, 'error': 'Not enough stock available'}), 400
        
        # Update cart
        cart = session.get('cart', {})
        if quantity == 0:
            cart.pop(item_id, None)
        else:
            cart[item_id] = quantity
        
        session.modified = True
        
        return jsonify({
            'success': True,
            'cart_count': len(cart),
            'message': 'Cart updated successfully'
        })
        
    except Exception as e:
        print(f"Error updating cart: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while updating cart'}), 500

@app.route('/cart/remove', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400
        
        item_id = data.get('item_id')
        if not item_id:
            return jsonify({'success': False, 'error': 'Invalid item ID'}), 400
        
        # Remove item from cart
        cart = session.get('cart', {})
        if item_id in cart:
            del cart[item_id]
            session.modified = True
        
        return jsonify({
            'success': True,
            'cart_count': len(cart),
            'message': 'Item removed from cart successfully'
        })
        
    except Exception as e:
        print(f"Error removing from cart: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while removing item from cart'}), 500

@app.route('/cart/checkout', methods=['POST'])
@login_required
def checkout():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        cart = session.get('cart', {})
        if not cart:
            return jsonify({'success': False, 'error': 'Cart is empty'}), 400
        
        cart_items = []
        total_amount = 0
        
        # Validate cart items and update inventory
        for item_id, quantity in cart.items():
            try:
                # Get item from inventory
                item = mongo.db.inventory.find_one({
                    '_id': ObjectId(item_id),
                    'user_id': ObjectId(session['user_id'])
                })
                
                if not item:
                    return jsonify({'success': False, 'error': f'Item {item_id} not found'}), 404
                
                if quantity > item['quantity']:
                    return jsonify({'success': False, 'error': f'Not enough stock for {item["name"]}'}), 400
                
                # Update inventory
                result = mongo.db.inventory.update_one(
                    {'_id': item['_id']},
                    {'$inc': {'quantity': -quantity}}
                )
                
                if result.modified_count == 0:
                    return jsonify({'success': False, 'error': f'Failed to update inventory for {item["name"]}'}), 500
                
                # Add to cart items
                cart_items.append({
                    'item_id': str(item['_id']),
                    'name': item['name'],
                    'quantity': quantity,
                    'price': item['price'],
                    'purchase_price': item.get('purchase_price', 0),
                    'total': quantity * item['price']
                })
                
                total_amount += quantity * item['price']
                
            except Exception as e:
                print(f"Error processing item {item_id}: {str(e)}")
                return jsonify({'success': False, 'error': f'Error processing item {item_id}'}), 500
        
        # Create transaction record
        transaction = {
            'user_id': ObjectId(session['user_id']),
            'items': cart_items,
            'total_amount': total_amount,
            'total_cost': sum(item['purchase_price'] * item['quantity'] for item in cart_items),
            'profit': sum((item['price'] - item['purchase_price']) * item['quantity'] for item in cart_items),
            'created_at': datetime.utcnow(),
            'status': 'completed'
        }
        
        result = mongo.db.transactions.insert_one(transaction)
        if not result.inserted_id:
            return jsonify({'success': False, 'error': 'Failed to create transaction record'}), 500
        
        # Clear the cart
        session.pop('cart', None)
        session.modified = True
        
        return jsonify({
            'success': True,
            'message': 'Order placed successfully',
            'transaction_id': str(result.inserted_id)
        })
        
    except Exception as e:
        print(f"Error during checkout: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred during checkout'
        }), 500

@app.route('/ai')
def ai_services():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get all categories for the prediction form
    categories = mongo.db.inventory.distinct('category', {'user_id': ObjectId(session['user_id'])})
    return render_template('ai_services.html', categories=categories)

@app.route('/get_inventory_prediction', methods=['POST'])
def get_inventory_prediction():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        category = data.get('category')
        prediction_period = data.get('prediction_period', 30)
        
        # Get historical transaction data for the category
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)  # Use last 90 days for training
        
        pipeline = [
            {
                '$match': {
                    'user_id': ObjectId(session['user_id']),
                    'created_at': {'$gte': start_date, '$lte': end_date}
                }
            },
            {'$unwind': '$items'},
            {
                '$lookup': {
                    'from': 'inventory',
                    'localField': 'items.item_id',
                    'foreignField': '_id',
                    'as': 'inventory_item'
                }
            },
            {'$unwind': '$inventory_item'},
            {
                '$match': {
                    'inventory_item.category': category
                }
            },
            {
                '$group': {
                    '_id': {
                        'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
                        'item_id': '$items.item_id',
                        'name': '$items.name'
                    },
                    'quantity_sold': {'$sum': '$items.quantity'}
                }
            }
        ]
        
        sales_data = list(mongo.db.transactions.aggregate(pipeline))
        
        if not sales_data:
            return jsonify({
                'success': False,
                'error': 'No historical data available for prediction'
            }), 400
        
        # Prepare data for prediction
        predictions = []
        unique_items = set(item['_id']['name'] for item in sales_data)
        
        for item_name in unique_items:
            item_sales = [s for s in sales_data if s['_id']['name'] == item_name
                        if len(item_sales) >= 7]  # Need minimum data points
            
            if item_sales:
                # Prepare time series data
                dates = [(datetime.strptime(s['_id']['date'], '%Y-%m-%d') - start_date).days 
                        for s in item_sales]
                quantities = [s['quantity_sold'] for s in item_sales]
                
                # Reshape data for sklearn
                X = np.array(dates).reshape(-1, 1)
                y = np.array(quantities)
                
                # Train model
                model = LinearRegression()
                model.fit(X, y)
                
                # Predict future demand
                future_days = np.array(range(90, 90 + prediction_period)).reshape(-1, 1)
                predicted_demand = model.predict(future_days)
                
                # Calculate average daily demand
                avg_daily_demand = max(0, np.mean(predicted_demand))
                total_predicted = int(avg_daily_demand * prediction_period)
                
                predictions.append({
                    'item': item_name,
                    'prediction': total_predicted
                })
        
        return jsonify({
            'success': True,
            'message': f'Predictions for the next {prediction_period} days',
            'predictions': predictions
        })
        
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while generating predictions'
        }), 500

@app.route('/analyze_sales', methods=['POST'])
def analyze_sales():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        analysis_period = data.get('analysis_period', 30)
        
        # Get sales data for the period
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=analysis_period)
        
        pipeline = [
            {
                '$match': {
                    'user_id': ObjectId(session['user_id']),
                    'created_at': {'$gte': start_date, '$lte': end_date}
                }
            },
            {
                '$group': {
                    '_id': None,
                    'total_sales': {'$sum': '$total_amount'},
                    'transaction_count': {'$sum': 1},
                    'items': {'$push': '$items'}
                }
            }
        ]
        
        sales_data = list(mongo.db.transactions.aggregate(pipeline))
        
        if not sales_data:
            return jsonify({
                'success': False,
                'error': 'No sales data available for analysis'
            }), 400
        
        sales_data = sales_data[0]
        
        # Flatten items list
        all_items = [item for transaction in sales_data['items'] for item in transaction]
        
        # Calculate metrics
        total_sales = sales_data['total_sales']
        total_transactions = sales_data['transaction_count']
        avg_transaction_value = total_sales / total_transactions if total_transactions > 0 else 0
        
        # Find top selling items
        item_sales = {}
        for item in all_items:
            if item['name'] not in item_sales:
                item_sales[item['name']] = {'quantity': 0, 'revenue': 0}
            item_sales[item['name']]['quantity'] += item['quantity']
            item_sales[item['name']]['revenue'] += item['total']
        
        top_items = sorted(item_sales.items(), key=lambda x: x[1]['revenue'], reverse=True)[:5]
        
        # Calculate daily sales trend
        daily_sales_pipeline = [
            {
                '$match': {
                    'user_id': ObjectId(session['user_id']),
                    'created_at': {'$gte': start_date, '$lte': end_date}
                }
            },
            {
                '$group': {
                    '_id': {
                        'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}}
                    },
                    'daily_sales': {'$sum': '$total_amount'}
                }
            },
            {'$sort': {'_id.date': 1}}
        ]
        
        daily_sales = list(mongo.db.transactions.aggregate(daily_sales_pipeline))
        
        # Calculate sales trend
        if len(daily_sales) > 1:
            sales_values = [day['daily_sales'] for day in daily_sales]
            trend = np.polyfit(range(len(sales_values)), sales_values, 1)[0]
            trend_percentage = (trend / np.mean(sales_values)) * 100
        else:
            trend_percentage = 0
        
        insights = {
            'Total Sales': f"${total_sales:,.2f}",
            'Number of Transactions': total_transactions,
            'Average Transaction Value': f"${avg_transaction_value:,.2f}",
            'Sales Trend': f"{'↑' if trend_percentage > 0 else '↓'} {abs(trend_percentage):.1f}%",
            'Top Selling Item': f"{top_items[0][0]} (${top_items[0][1]['revenue']:,.2f})" if top_items else "N/A"
        }
        
        return jsonify({
            'success': True,
            'message': f'Analysis for the last {analysis_period} days',
            'insights': insights
        })
        
    except Exception as e:
        print(f"Analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while analyzing sales data'
        }), 500

@app.route('/api/dashboard/data')
def get_dashboard_data():
    if not session.get('user_id'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        days = int(request.args.get('days', 30))
        user_id = ObjectId(session['user_id'])
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get transactions for the period
        transactions = list(mongo.db.transactions.find({
            'user_id': user_id,
            'created_at': {'$gte': start_date, '$lte': end_date}
        }).sort('created_at', 1))
        
        # Get inventory items
        inventory_items = list(mongo.db.inventory.find({'user_id': user_id}))
        
        # Calculate metrics
        cash_flow = sum(t['total_amount'] for t in transactions)
        operating_costs = cash_flow * 0.3
        
        # Calculate operating margin
        operating_margin = ((cash_flow - operating_costs) / cash_flow * 100) if cash_flow > 0 else 0
        
        # Calculate stock efficiency
        total_stock = sum(item['quantity'] for item in inventory_items)
        stock_sold = sum(sum(item['quantity'] for item in t['items']) for t in transactions)
        stock_efficiency = (stock_sold / total_stock * 100) if total_stock > 0 else 0
        
        # Calculate revenue growth
        prev_start_date = start_date - timedelta(days=days)
        prev_transactions = list(mongo.db.transactions.find({
            'user_id': user_id,
            'created_at': {'$gte': prev_start_date, '$lt': start_date}
        }))
        prev_revenue = sum(t['total_amount'] for t in prev_transactions)
        revenue_growth = ((cash_flow - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        
        # Calculate daily metrics
        daily_data = {}
        for t in transactions:
            date_key = t['created_at'].strftime('%Y-%m-%d')
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'revenue': 0,
                    'profit': 0,
                    'transactions': 0
                }
            daily_data[date_key]['revenue'] += t['total_amount']
            daily_data[date_key]['profit'] += t['total_amount'] * 0.3  # Example: 30% profit margin
            daily_data[date_key]['transactions'] += 1
        
        # Fill in missing dates
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_key = current_date.strftime('%Y-%m-%d')
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'revenue': 0,
                    'profit': 0,
                    'transactions': 0
                }
            date_list.append(date_key)
            current_date += timedelta(days=1)
        
        # Sort dates and prepare chart data
        date_list.sort()
        chart_data = {
            'dates': date_list,
            'revenue': [daily_data[d]['revenue'] for d in date_list],
            'profit': [daily_data[d]['profit'] for d in date_list],
            'transactions': [daily_data[d]['transactions'] for d in date_list]
        }
        
        # Calculate category performance
        category_data = {}
        for t in transactions:
            for item in t['items']:
                inventory_item = mongo.db.inventory.find_one({'_id': ObjectId(item['item_id'])})
                if inventory_item:
                    category = inventory_item.get('category', 'Uncategorized')
                    if category not in category_data:
                        category_data[category] = {
                            'revenue': 0,
                            'profit': 0,
                            'units': 0
                        }
                    category_data[category]['revenue'] += item['total']
                    category_data[category]['profit'] += item['total'] * 0.3
                    category_data[category]['units'] += item['quantity']
        
        # Prepare response data
        response_data = {
            'chart_data': chart_data,
            'metrics': {
                'cash_flow': cash_flow,
                'operating_margin': operating_margin,
                'stock_efficiency': stock_efficiency,
                'revenue_growth': revenue_growth
            },
            'category_performance': [
                {
                    'category': cat,
                    'revenue': data['revenue'],
                    'profit': data['profit'],
                    'units': data['units'],
                    'profit_margin': (data['profit'] / data['revenue'] * 100) if data['revenue'] > 0 else 0
                }
                for cat, data in category_data.items()
            ]
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error getting dashboard data: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching dashboard data'}), 500

if __name__ == '__main__':
    def get_all_ips():
        ips = []
        try:
            # Get hostname first
            hostname = socket.gethostname()
            ips.append(socket.gethostbyname(hostname))
            
            # Try getting other network interfaces
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr['addr']
                        if not ip.startswith('127.'):
                            ips.append(ip)
        except Exception as e:
            print(f"Error getting IPs: {e}")
        return list(set(ips))  # Remove duplicates

    port = 3000
    
    print("\nBizVentory Server Starting...")
    print("============================")
    print(f"Local access:     http://localhost:{port}")
    print("\nTry these URLs on other devices:")
    
    # Get and display all possible IPs
    ips = get_all_ips()
    for ip in ips:
        print(f"                http://{ip}:{port}")
    
    print(f"\nAlso try using computer name:")
    print(f"                http://{socket.gethostname()}:{port}")
    
    print("\nMake sure:")
    print("1. Other devices are on the same WiFi network")
    print("2. Windows Defender Firewall is disabled")
    print("3. Network is set to 'Private' in Windows settings")
    print("4. Mobile data is turned off on phones")
    print("\nPress Ctrl+C to stop the server")
    print("============================\n")
    
    # Run the app with explicit host and port
    app.run(
        host='0.0.0.0',  # Makes the server externally visible
        port=port,
        debug=True
    )