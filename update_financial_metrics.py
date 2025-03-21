from app import mongo
from datetime import datetime, timedelta
from bson import ObjectId
import random
import numpy as np

def calculate_profit_margins(cost_price, sell_price):
    """Calculate profit margins and markup"""
    profit = sell_price - cost_price
    profit_margin = (profit / sell_price) * 100 if sell_price > 0 else 0
    markup = (profit / cost_price) * 100 if cost_price > 0 else 0
    return profit, profit_margin, markup

def generate_realistic_prices(base_price):
    """Generate realistic purchase and selling prices"""
    # Purchase price is 60-80% of selling price
    purchase_price = base_price * random.uniform(0.6, 0.8)
    # Add some random variation to selling price
    selling_price = base_price * random.uniform(0.95, 1.05)
    return round(purchase_price, 2), round(selling_price, 2)

def update_financial_metrics():
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
        
        # Update inventory items with purchase prices and profit calculations
        bulk_updates = []
        total_inventory_value = 0
        total_potential_profit = 0

        for item in inventory_items:
            try:
                # Generate realistic purchase and selling prices
                base_price = item.get('price', 0)
                purchase_price, selling_price = generate_realistic_prices(base_price)
                profit, profit_margin, markup = calculate_profit_margins(purchase_price, selling_price)
                
                # Calculate inventory values
                quantity = item.get('quantity', 0)
                inventory_value = purchase_price * quantity
                potential_profit = profit * quantity
                
                total_inventory_value += inventory_value
                total_potential_profit += potential_profit

                # Update item with financial metrics
                update = {
                    '$set': {
                        'purchase_price': purchase_price,
                        'selling_price': selling_price,
                        'price': selling_price,  # Update the original price field
                        'profit_per_unit': round(profit, 2),
                        'profit_margin': round(profit_margin, 2),
                        'markup_percentage': round(markup, 2),
                        'inventory_value': round(inventory_value, 2),
                        'potential_profit': round(potential_profit, 2),
                        'last_updated': datetime.utcnow()
                    }
                }
                bulk_updates.append(UpdateOne({'_id': item['_id']}, update))
            except Exception as item_error:
                print(f"Error processing item {item.get('name', 'Unknown')}: {str(item_error)}")
                continue

        # Update all inventory items
        if bulk_updates:
            result = mongo.db.inventory.bulk_write(bulk_updates)
            print(f"Updated {result.modified_count} inventory items with financial metrics")

        # Get updated inventory items for sales calculations
        updated_items = {str(item['_id']): item for item in mongo.db.inventory.find({'user_id': user['_id']})}

        # Update sales records with profit calculations
        sales_updates = []
        total_sales_revenue = 0
        total_sales_profit = 0

        # Get all sales for the user
        sales = list(mongo.db.sales.find({'user_id': user['_id']}))
        for sale in sales:
            try:
                item = updated_items.get(str(sale['item_id']))
                if item:
                    # Calculate sale profit
                    sale_cost = sale['quantity'] * item['purchase_price']
                    sale_revenue = sale['quantity'] * sale['price']
                    sale_profit = sale_revenue - sale_cost
                    
                    total_sales_revenue += sale_revenue
                    total_sales_profit += sale_profit

                    # Update sale with profit calculations
                    update = {
                        '$set': {
                            'cost_price': item['purchase_price'],
                            'revenue': round(sale_revenue, 2),
                            'profit': round(sale_profit, 2),
                            'profit_margin': round((sale_profit / sale_revenue) * 100 if sale_revenue > 0 else 0, 2)
                        }
                    }
                    sales_updates.append(UpdateOne({'_id': sale['_id']}, update))
            except Exception as sale_error:
                print(f"Error processing sale {sale.get('_id', 'Unknown')}: {str(sale_error)}")
                continue

        # Update all sales records
        if sales_updates:
            result = mongo.db.sales.bulk_write(sales_updates)
            print(f"Updated {result.modified_count} sales records with profit calculations")

        # Create financial summary
        financial_summary = {
            'user_id': user['_id'],
            'total_inventory_value': round(total_inventory_value, 2),
            'total_potential_profit': round(total_potential_profit, 2),
            'total_sales_revenue': round(total_sales_revenue, 2),
            'total_sales_profit': round(total_sales_profit, 2),
            'average_profit_margin': round((total_sales_profit / total_sales_revenue) * 100 if total_sales_revenue > 0 else 0, 2),
            'last_updated': datetime.utcnow()
        }

        # Update or insert financial summary
        mongo.db.financial_summary.update_one(
            {'user_id': user['_id']},
            {'$set': financial_summary},
            upsert=True
        )

        print("\nFinancial Metrics Added Successfully!")
        print("\nNew Features Available:")
        print("\n1. Item-level Metrics:")
        print("   - Purchase Price")
        print("   - Selling Price")
        print("   - Profit per Unit")
        print("   - Profit Margin")
        print("   - Markup Percentage")
        
        print("\n2. Inventory Valuation:")
        print("   - Total Inventory Value")
        print("   - Potential Profit")
        print("   - Stock Value by Category")
        
        print("\n3. Sales Analytics:")
        print("   - Revenue per Sale")
        print("   - Profit per Sale")
        print("   - Profit Margins")
        
        print("\n4. Financial Summary:")
        print("   - Total Revenue")
        print("   - Total Profit")
        print("   - Average Profit Margin")
        
        print("\n5. Profitability Analysis:")
        print("   - Most Profitable Items")
        print("   - Best Performing Categories")
        print("   - Profit Trends")

        print("\nSummary of Current Financial Position:")
        print(f"Total Inventory Value: ${total_inventory_value:,.2f}")
        print(f"Total Potential Profit: ${total_potential_profit:,.2f}")
        print(f"Total Sales Revenue: ${total_sales_revenue:,.2f}")
        print(f"Total Sales Profit: ${total_sales_profit:,.2f}")
        print(f"Average Profit Margin: {(total_sales_profit / total_sales_revenue) * 100 if total_sales_revenue > 0 else 0:.2f}%")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    from pymongo import UpdateOne
    update_financial_metrics() 