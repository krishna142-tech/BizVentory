from app import mongo
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

def fix_user_auth():
    try:
        email = 'test@bizventory.com'
        password = 'Test@123'
        
        # Create new user data with all required fields
        user_data = {
            'email': email,
            'username': email,  # Adding username field
            'password': generate_password_hash(password, method='pbkdf2:sha256'),
            'business_name': 'Test Enterprise',
            'created_at': datetime.utcnow(),
            'active': True,  # Adding active status
            'settings': {
                'currency': 'USD',
                'low_stock_threshold': 10
            }
        }
        
        # Remove existing user if exists
        mongo.db.users.delete_many({'email': email})
        print("Cleared existing user")
        
        # Insert new user
        result = mongo.db.users.insert_one(user_data)
        if result.inserted_id:
            print("New user created successfully!")
            
            # Verify the user can be found and password works
            user = mongo.db.users.find_one({'email': email})
            if user and check_password_hash(user['password'], password):
                print("\nUser verification successful!")
                print("\nLogin credentials:")
                print(f"Email: {email}")
                print(f"Password: {password}")
            else:
                print("User verification failed!")
        else:
            print("Failed to create user!")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    fix_user_auth() 