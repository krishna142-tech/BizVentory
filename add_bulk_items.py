from app import mongo
from datetime import datetime, timedelta
from bson import ObjectId
import random

def generate_dates(num_days):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=num_days)
    return start_date + timedelta(days=random.randint(0, num_days))

def add_bulk_items():
    try:
        # Get the test user
        user = mongo.db.users.find_one({'username': 'spirit@tech.com'})
        if not user:
            print("Test user not found!")
            return

        # Categories and their brands
        inventory_data = {
            'Electronics': {
                'Apple': ['iPhone 14', 'MacBook Pro', 'iPad Pro', 'AirPods Pro', 'Apple Watch'],
                'Samsung': ['Galaxy S23', 'Galaxy Tab', 'Smart TV 4K', 'Galaxy Buds', 'Gaming Monitor'],
                'Dell': ['XPS 13', 'Inspiron 15', 'Alienware', 'UltraSharp Monitor', 'Precision Tower'],
                'Sony': ['PlayStation 5', 'WH-1000XM4', 'Bravia TV', 'Alpha Camera', 'Sound Bar'],
                'LG': ['OLED TV', 'Gaming Monitor', 'Sound System', 'Refrigerator', 'Washing Machine']
            },
            'Furniture': {
                'IKEA': ['Office Desk', 'Bookshelf', 'Dining Table', 'Wardrobe', 'Sofa Set'],
                'Herman Miller': ['Ergonomic Chair', 'Standing Desk', 'Office Set', 'Desk Lamp', 'Storage Unit'],
                'Ashley': ['Bedroom Set', 'Living Room Set', 'Dining Set', 'Office Chair', 'Coffee Table']
            },
            'Clothing': {
                'Nike': ['Running Shoes', 'Sports Jacket', 'Training Pants', 'Gym Bag', 'Athletic Socks'],
                'Adidas': ['Soccer Cleats', 'Track Suit', 'Training Shirt', 'Sports Bag', 'Running Shorts'],
                'Puma': ['Tennis Shoes', 'Sports Watch', 'Workout Gear', 'Backpack', 'Fitness Tracker']
            },
            'Books': {
                'Penguin': ['Business Guide', 'Tech Manual', 'Science Book', 'History Collection', 'Art Book'],
                'Oxford': ['Dictionary', 'Encyclopedia', 'Research Paper', 'Study Guide', 'Academic Journal'],
                'Pearson': ['Textbook', 'Workbook', 'Reference Guide', 'Lab Manual', 'Course Material']
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
                        min_quantity = max(2, quantity // 5)  # 20% of quantity as min
                        price = round(random.uniform(50, 2000), 2)
                        
                        # Generate dates within last 180 days
                        created_date = generate_dates(180)
                        updated_date = created_date + timedelta(days=random.randint(0, 30))
                        
                        # Add variant suffix if needed
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
                            'updated_at': updated_date
                        }
                        bulk_items.append(item)

        # Insert items into MongoDB
        result = mongo.db.inventory.insert_many(bulk_items)
        if result.inserted_ids:
            print(f"Successfully added {len(result.inserted_ids)} items!")
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
        else:
            print("Failed to add items")

    except Exception as e:
        print(f"Error adding items: {str(e)}")

if __name__ == '__main__':
    add_bulk_items() 