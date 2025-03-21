from app import mongo
from datetime import datetime, timedelta
from bson import ObjectId
import random
import numpy as np
from sklearn.linear_model import LinearRegression

def generate_purchase_date(item_created_date):
    """Generate a realistic purchase date before the item creation"""
    max_days_before = 30  # Maximum days before creation date
    days_before = random.randint(1, max_days_before)
    return item_created_date - timedelta(days=days_before)

def calculate_kpis(sales_data, inventory_value):
    """Calculate key financial KPIs"""
    total_revenue = sum(sale['revenue'] for sale in sales_data)
    total_cost = sum(sale['quantity'] * sale['cost_price'] for sale in sales_data)
    total_profit = sum(sale['profit'] for sale in sales_data)
    
    # Calculate KPIs
    kpis = {
        'gross_profit_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
        'inventory_turnover': (total_cost / inventory_value) if inventory_value > 0 else 0,
        'return_on_investment': (total_profit / inventory_value * 100) if inventory_value > 0 else 0,
        'average_transaction_value': (total_revenue / len(sales_data)) if sales_data else 0
    }
    return {k: round(v, 2) for k, v in kpis.items()}

def predict_future_sales(dates, values, days_to_predict=30):
    """Predict future sales using linear regression"""
    X = np.array([(d - dates[0]).days for d in dates]).reshape(-1, 1)
    y = np.array(values)
    
    model = LinearRegression()
    model.fit(X, y)
    
    future_days = np.array(range(X[-1][0] + 1, X[-1][0] + days_to_predict + 1)).reshape(-1, 1)
    predictions = model.predict(future_days)
    
    return [dates[-1] + timedelta(days=i+1) for i in range(days_to_predict)], predictions

def enhance_financial_analytics():
    try:
        # Get the test user
        user = mongo.db.users.find_one({'email': 'test@bizventory.com'})
        if not user:
            print("User not found!")
            return

        # Get all inventory items
        inventory_items = list(mongo.db.inventory.find({'user_id': user['_id']}))
        if not inventory_items:
            print("No inventory items found!")
            return

        print(f"Found {len(inventory_items)} inventory items")
        
        # Update inventory items with purchase dates and enhanced metrics
        bulk_updates = []
        category_metrics = {}
        brand_metrics = {}

        for item in inventory_items:
            try:
                # Generate purchase date
                purchase_date = generate_purchase_date(item.get('created_at', datetime.utcnow()))
                
                # Update item with purchase date and enhanced metrics
                update = {
                    '$set': {
                        'purchase_date': purchase_date,
                        'days_in_inventory': (datetime.utcnow() - purchase_date).days,
                        'holding_cost': round(item['purchase_price'] * 0.002 * (datetime.utcnow() - purchase_date).days, 2),  # 0.2% daily holding cost
                        'last_updated': datetime.utcnow()
                    }
                }
                bulk_updates.append(UpdateOne({'_id': item['_id']}, update))

                # Aggregate category metrics
                category = item.get('category', 'Uncategorized')
                if category not in category_metrics:
                    category_metrics[category] = {
                        'total_value': 0,
                        'total_profit': 0,
                        'item_count': 0
                    }
                category_metrics[category]['total_value'] += item['inventory_value']
                category_metrics[category]['total_profit'] += item['potential_profit']
                category_metrics[category]['item_count'] += 1

                # Aggregate brand metrics
                brand = item.get('brand', 'Unknown')
                if brand not in brand_metrics:
                    brand_metrics[brand] = {
                        'total_value': 0,
                        'total_profit': 0,
                        'item_count': 0
                    }
                brand_metrics[brand]['total_value'] += item['inventory_value']
                brand_metrics[brand]['total_profit'] += item['potential_profit']
                brand_metrics[brand]['item_count'] += 1

            except Exception as item_error:
                print(f"Error processing item {item.get('name', 'Unknown')}: {str(item_error)}")
                continue

        # Update inventory items
        if bulk_updates:
            result = mongo.db.inventory.bulk_write(bulk_updates)
            print(f"Updated {result.modified_count} inventory items with purchase dates and enhanced metrics")

        # Get all sales for trend analysis
        sales = list(mongo.db.sales.find({'user_id': user['_id']}))
        
        # Prepare daily sales data for visualization
        daily_sales = {}
        daily_profits = {}
        for sale in sales:
            date = sale['date'].date()
            daily_sales[date] = daily_sales.get(date, 0) + sale['revenue']
            daily_profits[date] = daily_profits.get(date, 0) + sale['profit']

        # Sort by date
        dates = sorted(daily_sales.keys())
        revenues = [daily_sales[date] for date in dates]
        profits = [daily_profits[date] for date in dates]

        # Generate sales predictions
        future_dates, predicted_sales = predict_future_sales(dates, revenues)
        _, predicted_profits = predict_future_sales(dates, profits)

        # Calculate KPIs
        kpis = calculate_kpis(sales, sum(item['inventory_value'] for item in inventory_items))

        # Create visualization data
        visualization_data = {
            'user_id': user['_id'],
            'daily_sales': [
                {'date': date.isoformat(), 'revenue': daily_sales[date], 'profit': daily_profits[date]}
                for date in dates
            ],
            'predictions': [
                {'date': date.isoformat(), 'predicted_revenue': max(0, rev), 'predicted_profit': max(0, prof)}
                for date, rev, prof in zip(future_dates, predicted_sales, predicted_profits)
            ],
            'category_performance': [
                {
                    'category': cat,
                    'total_value': metrics['total_value'],
                    'total_profit': metrics['total_profit'],
                    'item_count': metrics['item_count'],
                    'profit_margin': (metrics['total_profit'] / metrics['total_value'] * 100) if metrics['total_value'] > 0 else 0
                }
                for cat, metrics in category_metrics.items()
            ],
            'brand_performance': [
                {
                    'brand': brand,
                    'total_value': metrics['total_value'],
                    'total_profit': metrics['total_profit'],
                    'item_count': metrics['item_count'],
                    'profit_margin': (metrics['total_profit'] / metrics['total_value'] * 100) if metrics['total_value'] > 0 else 0
                }
                for brand, metrics in brand_metrics.items()
            ],
            'kpis': kpis,
            'last_updated': datetime.utcnow()
        }

        # Update visualization data
        mongo.db.visualization_data.update_one(
            {'user_id': user['_id']},
            {'$set': visualization_data},
            upsert=True
        )

        print("\nEnhanced Financial Analytics Added Successfully!")
        print("\nNew Features Available:")
        
        print("\n1. Time-based Analytics:")
        print("   - Purchase Dates")
        print("   - Days in Inventory")
        print("   - Holding Costs")
        print("   - Historical Trends")
        
        print("\n2. Financial KPIs:")
        print(f"   - Gross Profit Margin: {kpis['gross_profit_margin']:.2f}%")
        print(f"   - Inventory Turnover: {kpis['inventory_turnover']:.2f}x")
        print(f"   - Return on Investment: {kpis['return_on_investment']:.2f}%")
        print(f"   - Average Transaction Value: ${kpis['average_transaction_value']:.2f}")
        
        print("\n3. Category Performance:")
        for cat_data in sorted(visualization_data['category_performance'], 
                             key=lambda x: x['total_profit'], reverse=True)[:3]:
            print(f"   - {cat_data['category']}: ${cat_data['total_profit']:,.2f} profit")
        
        print("\n4. Brand Performance:")
        for brand_data in sorted(visualization_data['brand_performance'], 
                               key=lambda x: x['total_profit'], reverse=True)[:3]:
            print(f"   - {brand_data['brand']}: ${brand_data['total_profit']:,.2f} profit")
        
        print("\n5. Predictions (30 days):")
        print(f"   - Predicted Revenue: ${sum(predicted_sales):,.2f}")
        print(f"   - Predicted Profit: ${sum(predicted_profits):,.2f}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    from pymongo import UpdateOne
    enhance_financial_analytics() 