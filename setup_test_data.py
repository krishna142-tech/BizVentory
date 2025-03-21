from app import mongo
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash

def setup_test_data():
    try:
        # First, create or update the user
        user_data = {
            'username': 'spirit@techy.com',
            'password': generate_password_hash('Saroj@142'),
            'business_name': 'Test Business',
            'created_at': datetime.utcnow(),
            'settings': {
                'currency': 'USD',
                'low_stock_threshold': 10
            }
        }
        
        # Update or insert user
        result = mongo.db.users.update_one(
            {'username': 'spirit@techy.com'},
            {'$set': user_data},
            upsert=True
        )
        
        print("User created/updated successfully")
        
        # Get the user
        user = mongo.db.users.find_one({'username': 'spirit@techy.com'})
        if not user:
            print("Error: User not found after creation!")
            return

        # Clear existing inventory for this user
        mongo.db.inventory.delete_many({'user_id': user['_id']})
        print("Cleared existing inventory items")

        # Sample inventory data
        inventory_data = {
            'Electronics': {
                'Apple': ['iPhone 14', 'MacBook Pro', 'iPad Pro', 'AirPods Pro', 'Apple Watch'],
                'Samsung': ['Galaxy S23', 'Galaxy Tab', 'Smart TV 4K', 'Galaxy Buds', 'Gaming Monitor'],
                'Dell': ['XPS 13', 'Inspiron 15', 'Alienware', 'UltraSharp Monitor', 'Precision Tower']
            },
            'Furniture': {
                'IKEA': ['Office Desk', 'Bookshelf', 'Dining Table', 'Wardrobe', 'Sofa Set'],
                'Herman Miller': ['Ergonomic Chair', 'Standing Desk', 'Office Set', 'Desk Lamp', 'Storage Unit']
            },
            'Clothing': {
                'Nike': ['Running Shoes', 'Sports Jacket', 'Training Pants', 'Gym Bag', 'Athletic Socks'],
                'Adidas': ['Soccer Cleats', 'Track Suit', 'Training Shirt', 'Sports Bag', 'Running Shorts']
            }
        }

        bulk_items = []
        for category, brands in inventory_data.items():
            for brand, products in brands.items():
                for product in products:
                    # Generate 2-3 variants for each product
                    variants = random.randint(2, 3)
                    for _ in range(variants):
                        quantity = random.randint(1, 50)
                        min_quantity = max(2, quantity // 5)
                        price = round(random.uniform(50, 2000), 2)
                        
                        # Generate dates within last 180 days
                        end_date = datetime.utcnow()
                        start_date = end_date - timedelta(days=180)
                        created_date = start_date + timedelta(days=random.randint(0, 180))
                        updated_date = created_date + timedelta(days=random.randint(0, 30))
                        
                        variant_name = f"{product} {['Pro', 'Lite', 'Plus', 'Max', 'Basic'][random.randint(0, 4)]}" if variants > 1 else product
                        
                        item = {
                            'name': variant_name,
                            'brand': brand,
                            'category': category,
                            'quantity': quantity,
                            'price': price,
                            'min_quantity': min_quantity,
                            'user_id': user['_id'],
                            'created_at': created_date,
                            'updated_at': updated_date,
                            'description': f"Sample {category} product from {brand}"
                        }
                        bulk_items.append(item)

        # Insert items into MongoDB
        result = mongo.db.inventory.insert_many(bulk_items)
        if result.inserted_ids:
            print(f"\nSuccessfully added {len(result.inserted_ids)} items!")
            print("\nSummary by category:")
            category_summary = {}
            for item in bulk_items:
                cat = item['category']
                category_summary[cat] = category_summary.get(cat, 0) + 1
            
            for cat, count in category_summary.items():
                print(f"- {cat}: {count} items")
                
            print("\nSample items from each category:")
            shown_categories = set()
            for item in bulk_items:
                if item['category'] not in shown_categories:
                    print(f"- {item['name']} ({item['brand']}) - {item['category']} - Quantity: {item['quantity']}")
                    shown_categories.add(item['category'])
                    
            print("\nLogin credentials:")
            print("Username: spirit@techy.com")
            print("Password: Saroj@142")
        else:
            print("Failed to add items")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    setup_test_data()