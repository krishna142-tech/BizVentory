from app import mongo
from werkzeug.security import generate_password_hash
from datetime import datetime

def add_test_user():
    try:
        # Check if user already exists
        existing_user = mongo.db.users.find_one({'username': 'spirit@tech.com'})
        if existing_user:
            print("User already exists!")
            return

        # Create new user document
        new_user = {
            'username': 'spirit@tech.com',
            'password': generate_password_hash('Saroj@142'),
            'business_name': 'Test Business',
            'created_at': datetime.utcnow(),
            'settings': {
                'currency': 'USD',
                'low_stock_threshold': 10
            }
        }
        
        # Insert into MongoDB
        result = mongo.db.users.insert_one(new_user)
        if result.inserted_id:
            print("Test user created successfully!")
        else:
            print("Failed to create user")
            
    except Exception as e:
        print(f"Error creating user: {str(e)}")

if __name__ == '__main__':
    add_test_user() 