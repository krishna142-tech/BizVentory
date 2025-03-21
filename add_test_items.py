from app import mongo
from datetime import datetime
from bson import ObjectId

def add_test_items():
    try:
        # Get the test user
        user = mongo.db.users.find_one({'username': 'spirit@tech.com'})
        if not user:
            print("Test user not found!")
            return

        # Sample inventory items
        test_items = [
            {
                'name': 'Laptop Dell XPS 13',
                'brand': 'Dell',
                'category': 'Electronics',
                'quantity': 15,
                'price': 1299.99,
                'min_quantity': 5,
                'user_id': user['_id'],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            },
            {
                'name': 'iPhone 14 Pro',
                'brand': 'Apple',
                'category': 'Electronics',
                'quantity': 8,
                'price': 999.99,
                'min_quantity': 3,
                'user_id': user['_id'],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            },
            {
                'name': 'Samsung 4K TV',
                'brand': 'Samsung',
                'category': 'Electronics',
                'quantity': 4,
                'price': 799.99,
                'min_quantity': 2,
                'user_id': user['_id'],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            },
            {
                'name': 'Office Desk',
                'brand': 'IKEA',
                'category': 'Furniture',
                'quantity': 12,
                'price': 249.99,
                'min_quantity': 4,
                'user_id': user['_id'],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            },
            {
                'name': 'Ergonomic Chair',
                'brand': 'Herman Miller',
                'category': 'Furniture',
                'quantity': 6,
                'price': 899.99,
                'min_quantity': 2,
                'user_id': user['_id'],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ]

        # Insert items into MongoDB
        result = mongo.db.inventory.insert_many(test_items)
        if result.inserted_ids:
            print(f"Successfully added {len(result.inserted_ids)} test items!")
            print("\nAdded items:")
            for item in test_items:
                print(f"- {item['name']} ({item['brand']}) - Quantity: {item['quantity']}")
        else:
            print("Failed to add test items")

    except Exception as e:
        print(f"Error adding test items: {str(e)}")

if __name__ == '__main__':
    add_test_items() 