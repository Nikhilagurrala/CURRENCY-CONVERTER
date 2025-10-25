#!/usr/bin/env python3
"""
Test script for the Currency Converter Web Application
"""

import os
import sys
import requests
import time
from app import app, db, Currency, ExchangeRate

def test_database_setup():
    """Test database initialization and currency loading"""
    print("Testing database setup...")
    
    with app.app_context():
        # Check if currencies are loaded
        currency_count = Currency.query.count()
        print(f"✓ Loaded {currency_count} currencies")
        
        # Check if we have major currencies
        major_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']
        for code in major_currencies:
            currency = Currency.query.filter_by(code=code).first()
            if currency:
                print(f"✓ {code} - {currency.name} ({currency.country})")
            else:
                print(f"✗ Missing {code}")
        
        return currency_count > 50  # Should have 100+ currencies

def test_api_endpoints():
    """Test API endpoints"""
    print("\nTesting API endpoints...")
    
    with app.test_client() as client:
        # Test currencies endpoint
        response = client.get('/api/currencies')
        if response.status_code == 200:
            currencies = response.get_json()
            print(f"✓ /api/currencies returned {len(currencies)} currencies")
        else:
            print(f"✗ /api/currencies failed with status {response.status_code}")
            return False
        
        # Test conversion endpoint
        test_data = {
            'amount': 100,
            'from_currency': 'USD',
            'to_currency': 'EUR'
        }
        
        response = client.post('/api/convert', 
                             json=test_data,
                             content_type='application/json')
        
        if response.status_code == 200:
            result = response.get_json()
            if result.get('success'):
                print(f"✓ Conversion: {result['amount']} {result['from_currency']} = {result['result']} {result['to_currency']}")
            else:
                print(f"✗ Conversion failed: {result.get('error')}")
                return False
        else:
            print(f"✗ /api/convert failed with status {response.status_code}")
            return False
        
        return True

def test_web_interface():
    """Test web interface"""
    print("\nTesting web interface...")
    
    with app.test_client() as client:
        response = client.get('/')
        if response.status_code == 200:
            print("✓ Main page loads successfully")
            return True
        else:
            print(f"✗ Main page failed with status {response.status_code}")
            return False

def main():
    """Run all tests"""
    print("Currency Converter Web Application - Test Suite")
    print("=" * 50)
    
    # Set up test environment
    os.environ['EXCHANGE_API_KEY'] = 'test-key'  # Use test key for testing
    
    tests = [
        ("Database Setup", test_database_setup),
        ("API Endpoints", test_api_endpoints),
        ("Web Interface", test_web_interface)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
        
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application is ready to use.")
        print("\nTo start the application:")
        print("1. Get a free API key from https://www.exchangerate-api.com/")
        print("2. Create a .env file with: EXCHANGE_API_KEY=your_key_here")
        print("3. Run: python app.py")
        print("4. Open: http://localhost:5000")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
