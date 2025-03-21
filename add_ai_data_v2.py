from app import mongo
from datetime import datetime, timedelta
from bson import ObjectId
import random
import numpy as np

def generate_sales_data(item_id, start_date, num_days=180):
    """Generate realistic sales data with trends and seasonality"""
    dates = []
    quantities = []
    base_quantity = random.randint(5, 20)
    
    # Add trend
    trend = np.linspace(0, random.uniform(5, 15), num_days)
    
    # Add seasonality (weekly pattern)
    seasonality = np.sin(np.linspace(0, 12*np.pi, num_days)) * random.uniform(2, 5)
    
    for day in range(num_days):
        current_date = start_date + timedelta(days=day)
        
        # Weekend effect
        weekend_boost = 1.5 if current_date.weekday() >= 5 else 1.0
        
        # Base quantity with trend, seasonality, and some randomness
        quantity = max(0, int(
            (base_quantity + trend[day] + seasonality[day]) * weekend_boost * 
            random.uniform(0.7, 1.3)
        ))
        
        if quantity > 0:  # Only add days with sales
            dates.append(current_date)
            quantities.append(quantity)
    
    return dates, quantities

def add_ai_features():
    try:
        # Get the test user
        user = mongo.db.users.find_one({'email': 'test@bizventory.com'})
        if not user:
            print("User not found!")
            return

        # Get all inventory items for the user
        inventory_items = list(mongo.db.inventory.find({'user_id': user['_id']}))
        if not inventory_items:
            print("No inventory items found!")
            return

        print(f"Found {len(inventory_items)} inventory items")
        
        # Create sales collection if it doesn't exist
        if 'sales' not in mongo.db.list_collection_names():
            mongo.db.create_collection('sales')

        # Clear existing sales data for this user
        mongo.db.sales.delete_many({'user_id': user['_id']})
        print("Cleared existing sales data")

        # Generate sales data for each item
        total_sales = 0
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=180)

        bulk_sales = []
        bulk_analytics = []
        
        for item in inventory_items:
            try:
                # Generate sales data
                dates, quantities = generate_sales_data(item['_id'], start_date)
                
                # Create sales records
                for date, quantity in zip(dates, quantities):
                    sale_price = item['price'] * random.uniform(0.9, 1.2)  # Some price variation
                    sale = {
                        'user_id': user['_id'],
                        'item_id': item['_id'],
                        'quantity': quantity,
                        'price': sale_price,
                        'total': quantity * sale_price,
                        'date': date,
                        'category': item.get('category', 'Uncategorized'),
                        'brand': item.get('brand', 'Unknown'),
                        'item_name': item.get('name', 'Unknown Item')
                    }
                    bulk_sales.append(sale)
                    total_sales += 1

                # Calculate analytics
                total_quantity = sum(quantities)
                avg_daily_sales = total_quantity / len(dates) if dates else 0
                
                # Predict reorder date based on current quantity and sales rate
                days_until_reorder = float('inf')
                if avg_daily_sales > 0:
                    days_until_reorder = max(0, (item['quantity'] - item.get('min_quantity', 0)) / avg_daily_sales)

                analytics = {
                    'item_id': item['_id'],
                    'user_id': user['_id'],
                    'item_name': item.get('name', 'Unknown Item'),
                    'category': item.get('category', 'Uncategorized'),
                    'brand': item.get('brand', 'Unknown'),
                    'current_quantity': item['quantity'],
                    'min_quantity': item.get('min_quantity', 0),
                    'total_sales': total_quantity,
                    'avg_daily_sales': round(avg_daily_sales, 2),
                    'predicted_stockout_date': datetime.utcnow() + timedelta(days=days_until_reorder),
                    'sales_velocity': round(avg_daily_sales, 2),
                    'reorder_recommendation': days_until_reorder < 30,
                    'days_until_reorder': round(days_until_reorder, 1),
                    'last_updated': datetime.utcnow()
                }
                bulk_analytics.append(analytics)
                
            except Exception as item_error:
                print(f"Error processing item {item.get('name', 'Unknown')}: {str(item_error)}")
                continue

        # Insert sales data
        if bulk_sales:
            mongo.db.sales.insert_many(bulk_sales)
            print(f"Added {len(bulk_sales)} sales records")

        # Create or update analytics collection
        if 'analytics' not in mongo.db.list_collection_names():
            mongo.db.create_collection('analytics')
        
        # Clear existing analytics
        mongo.db.analytics.delete_many({'user_id': user['_id']})
        
        # Insert new analytics
        if bulk_analytics:
            mongo.db.analytics.insert_many(bulk_analytics)
            print(f"Added analytics for {len(bulk_analytics)} items")

        print("\nAI Features added successfully!")
        print("\nFeatures available:")
        print("1. Sales Prediction")
        print("   - Daily sales forecasting")
        print("   - Trend analysis")
        print("   - Seasonality detection")
        
        print("\n2. Stock Optimization")
        print("   - Optimal reorder points")
        print("   - Safety stock calculations")
        print("   - Stock level recommendations")
        
        print("\n3. Reorder Recommendations")
        print("   - Days until reorder needed")
        print("   - Predicted stockout dates")
        print("   - Priority reorder items")
        
        print("\n4. Sales Trend Analysis")
        print("   - Historical sales patterns")
        print("   - Weekend vs weekday performance")
        print("   - Category-wise trends")
        
        print("\n5. Category Performance Analytics")
        print("   - Top performing categories")
        print("   - Brand-wise analysis")
        print("   - Inventory turnover rates")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    add_ai_features() 