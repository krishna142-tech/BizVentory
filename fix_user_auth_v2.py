from app import mongo
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

def fix_user_auth():
    try:
        email = 'test@bizventory.com'
        password = 'Test@123'
        
        # First create a business
        business_data = {
            'name': 'Test Enterprise',
            'created_at': datetime.utcnow()
        }
        
        # Insert business
        business_result = mongo.db.businesses.insert_one(business_data)
        if not business_result.inserted_id:
            print("Failed to create business!")
            return
            
        print("Business created successfully")
        
        # Create new user data with all required fields
        user_data = {
            'email': email,
            'username': email,
            'password': generate_password_hash(password),  # Using default method
            'business_id': business_result.inserted_id,  # Link to business
            'business_name': 'Test Enterprise',
            'created_at': datetime.utcnow(),
            'active': True,
            'role': 'admin',  # Adding role
            'settings': {
                'currency': 'USD',
                'low_stock_threshold': 10,
                'timezone': 'UTC'
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
                
                # Update inventory user_id references
                mongo.db.inventory.update_many(
                    {'user_id': {'$exists': True}},
                    {'$set': {'user_id': result.inserted_id}}
                )
                print("\nUpdated inventory items with new user ID")
            else:
                print("User verification failed!")
        else:
            print("Failed to create user!")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    fix_user_auth() 