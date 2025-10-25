#!/usr/bin/env python3
"""
Startup script for Currency Converter Web Application
"""

import os
import sys
from app import app, db, init_currencies

def setup_application():
    """Initialize the application"""
    print("Currency Converter Web Application")
    print("=" * 40)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        print("✓ Database tables created")
        
        # Initialize currencies
        init_currencies()
        print("✓ Currencies initialized")
        
        # Check currency count
        from app import Currency
        count = Currency.query.count()
        print(f"✓ Loaded {count} currencies")
    
    print("\nApplication setup complete!")
    print("\nTo get started:")
    print("1. Get a free API key from: https://www.exchangerate-api.com/")
    print("2. Create a .env file with: EXCHANGE_API_KEY=your_key_here")
    print("3. The application will run on: http://localhost:5000")
    print("\nStarting server...")

def main():
    """Main startup function"""
    setup_application()
    
    # Check for API key
    api_key = os.getenv('EXCHANGE_API_KEY')
    if not api_key or api_key == 'your-api-key-here':
        print("\n⚠️  WARNING: No API key found!")
        print("The application will work with cached data only.")
        print("To enable real-time rates, set EXCHANGE_API_KEY in your .env file")
    
    # Start the application
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n\nApplication stopped by user")
    except Exception as e:
        print(f"\nError starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
