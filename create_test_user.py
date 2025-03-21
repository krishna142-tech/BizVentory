from app import mongo
from datetime import datetime
from werkzeug.security import generate_password_hash

def create_test_user():
    try:
        # Create new user data
        user_data = {
            'email': 'test@bizventory.com',  # Changed from username to email
            'password': generate_password_hash('Test@123'),
            'business_name': 'Test Enterprise',
            'created_at': datetime.utcnow(),
            'settings': {
                'currency': 'USD',
                'low_stock_threshold': 10
            }
        }
        
        # Check if user already exists
        existing_user = mongo.db.users.find_one({'email': 'test@bizventory.com'})
        if existing_user:
            print("User already exists! Updating password...")
            result = mongo.db.users.update_one(
                {'email': 'test@bizventory.com'},
                {'$set': {'password': user_data['password']}}
            )
            if result.modified_count > 0:
                print("Password updated successfully!")
            else:
                print("No changes were needed.")
            return
        
        # Insert new user
        result = mongo.db.users.insert_one(user_data)
        if result.inserted_id:
            print("New user created successfully!")
            print("\nLogin credentials:")
            print("Email: test@bizventory.com")
            print("Password: Test@123")
        else:
            print("Failed to create user!")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    create_test_user() 