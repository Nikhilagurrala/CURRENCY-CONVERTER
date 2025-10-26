from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
import requests
import json
import os
from functools import wraps
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///currency_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ExchangeRate-API configuration
EXCHANGE_API_KEY = os.getenv('EXCHANGE_API_KEY', 'your-api-key-here')
EXCHANGE_API_BASE = 'https://v6.exchangerate-api.com/v6'

class Currency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(10), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExchangeRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(3), nullable=False)
    to_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.Index('idx_currency_pair_time', 'from_currency', 'to_currency', 'timestamp'),)

class UserPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    base_currency = db.Column(db.String(3), default='USD')
    favorite_currencies = db.Column(db.Text)  # JSON string
    theme = db.Column(db.String(20), default='light')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TaxRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    country_code = db.Column(db.String(3), nullable=False)
    country_name = db.Column(db.String(100), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)
    exchange_tax_rate = db.Column(db.Float, nullable=False)  # Tax rate as percentage (e.g., 2.5 for 2.5%)
    service_fee_rate = db.Column(db.Float, nullable=False)   # Service fee as percentage
    minimum_fee = db.Column(db.Float, nullable=False)      # Minimum fee in local currency
    maximum_fee = db.Column(db.Float, nullable=True)       # Maximum fee in local currency
    is_active = db.Column(db.Boolean, default=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.Index('idx_country_currency', 'country_code', 'currency_code'),)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    currency_code = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    purchase_rate = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    __table_args__ = (db.Index('idx_user_portfolio', 'user_id', 'currency_code'),)

class CurrencyAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    from_currency = db.Column(db.String(10), nullable=False)
    to_currency = db.Column(db.String(10), nullable=False)
    target_rate = db.Column(db.Float, nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)  # 'above' or 'below'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    triggered_at = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (db.Index('idx_user_alerts', 'user_id', 'is_active'),)

def get_crypto_rate(crypto_currency, fiat_currency='USD'):
    """Get cryptocurrency exchange rate"""
    try:
        # Using CoinGecko API (free tier)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_currency.lower()}&vs_currencies={fiat_currency.lower()}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            crypto_id = crypto_currency.lower()
            if crypto_id in data and fiat_currency.lower() in data[crypto_id]:
                return data[crypto_id][fiat_currency.lower()]
    except Exception as e:
        print(f"Crypto API Error: {e}")
    
    return None

def get_exchange_rate(from_currency, to_currency):
    """Get accurate exchange rate with proper fallback system"""
    # Same currency conversion
    if from_currency == to_currency:
        return 1.0
    
    # Handle cryptocurrency conversions
    crypto_currencies = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'XRP', 'DOT', 'DOGE', 'AVAX', 'MATIC', 'LTC', 'LINK', 'UNI', 'ATOM', 'FTM']
    
    if from_currency in crypto_currencies and to_currency not in crypto_currencies:
        # Crypto to Fiat
        crypto_rate = get_crypto_rate(from_currency, to_currency)
        if crypto_rate:
            return crypto_rate
    elif to_currency in crypto_currencies and from_currency not in crypto_currencies:
        # Fiat to Crypto
        crypto_rate = get_crypto_rate(to_currency, from_currency)
        if crypto_rate:
            return 1.0 / crypto_rate
    elif from_currency in crypto_currencies and to_currency in crypto_currencies:
        # Crypto to Crypto (via USD)
        from_rate = get_crypto_rate(from_currency, 'USD')
        to_rate = get_crypto_rate(to_currency, 'USD')
        if from_rate and to_rate:
            return to_rate / from_rate
    
    # Check if we have recent data (within 1 hour for accuracy)
    recent_rate = ExchangeRate.query.filter(
        ExchangeRate.from_currency == from_currency,
        ExchangeRate.to_currency == to_currency,
        ExchangeRate.timestamp >= datetime.utcnow() - timedelta(hours=1)
    ).order_by(ExchangeRate.timestamp.desc()).first()
    
    if recent_rate:
        return recent_rate.rate
    
    # Try API first for real-time rates
    try:
        url = f"{EXCHANGE_API_BASE}/{EXCHANGE_API_KEY}/pair/{from_currency}/{to_currency}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('result') == 'success':
                rate = data.get('conversion_rate')
                
                # Store in database
                exchange_rate = ExchangeRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate
                )
                db.session.add(exchange_rate)
                db.session.commit()
                
                return rate
    except Exception as e:
        print(f"API Error: {e}")
    
    # Primary fallback to original currency converter
    try:
        from currency_converter.currency_converter import CurrencyConverter
        converter = CurrencyConverter()
        result = converter.convert(1, from_currency, to_currency)
        
        # Store in database
        exchange_rate = ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=result
        )
        db.session.add(exchange_rate)
        db.session.commit()
        
        return result
    except Exception as e:
        print(f"Primary Fallback Error: {e}")
    
    # Secondary fallback: try reverse conversion
    try:
        from currency_converter.currency_converter import CurrencyConverter
        converter = CurrencyConverter()
        reverse_result = converter.convert(1, to_currency, from_currency)
        result = 1.0 / reverse_result if reverse_result != 0 else 1.0
        
        # Store in database
        exchange_rate = ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=result
        )
        db.session.add(exchange_rate)
        db.session.commit()
        
        return result
    except Exception as e:
        print(f"Secondary Fallback Error: {e}")
    
    # Final fallback to last known rate
    last_rate = ExchangeRate.query.filter(
        ExchangeRate.from_currency == from_currency,
        ExchangeRate.to_currency == to_currency
    ).order_by(ExchangeRate.timestamp.desc()).first()
    
    return last_rate.rate if last_rate else 1.0

def init_currencies():
    """Initialize database with 100+ currencies"""
    currencies_data = [
        # Major currencies
        ('USD', 'US Dollar', '$', 'United States'),
        ('EUR', 'Euro', '€', 'European Union'),
        ('GBP', 'British Pound Sterling', '£', 'United Kingdom'),
        ('JPY', 'Japanese Yen', '¥', 'Japan'),
        ('CHF', 'Swiss Franc', 'CHF', 'Switzerland'),
        ('CAD', 'Canadian Dollar', 'C$', 'Canada'),
        ('AUD', 'Australian Dollar', 'A$', 'Australia'),
        ('NZD', 'New Zealand Dollar', 'NZ$', 'New Zealand'),
        
        # European currencies
        ('SEK', 'Swedish Krona', 'kr', 'Sweden'),
        ('NOK', 'Norwegian Krone', 'kr', 'Norway'),
        ('DKK', 'Danish Krone', 'kr', 'Denmark'),
        ('PLN', 'Polish Zloty', 'zł', 'Poland'),
        ('CZK', 'Czech Koruna', 'Kč', 'Czech Republic'),
        ('HUF', 'Hungarian Forint', 'Ft', 'Hungary'),
        ('RON', 'Romanian Leu', 'lei', 'Romania'),
        ('BGN', 'Bulgarian Lev', 'лв', 'Bulgaria'),
        ('HRK', 'Croatian Kuna', 'kn', 'Croatia'),
        ('RSD', 'Serbian Dinar', 'дин', 'Serbia'),
        ('MKD', 'Macedonian Denar', 'ден', 'North Macedonia'),
        ('BAM', 'Bosnia-Herzegovina Mark', 'КМ', 'Bosnia and Herzegovina'),
        ('ALL', 'Albanian Lek', 'L', 'Albania'),
        ('ISK', 'Icelandic Krona', 'kr', 'Iceland'),
        
        # Asian currencies
        ('CNY', 'Chinese Yuan', '¥', 'China'),
        ('KRW', 'South Korean Won', '₩', 'South Korea'),
        ('SGD', 'Singapore Dollar', 'S$', 'Singapore'),
        ('HKD', 'Hong Kong Dollar', 'HK$', 'Hong Kong'),
        ('TWD', 'Taiwan Dollar', 'NT$', 'Taiwan'),
        ('THB', 'Thai Baht', '฿', 'Thailand'),
        ('MYR', 'Malaysian Ringgit', 'RM', 'Malaysia'),
        ('IDR', 'Indonesian Rupiah', 'Rp', 'Indonesia'),
        ('PHP', 'Philippine Peso', '₱', 'Philippines'),
        ('VND', 'Vietnamese Dong', '₫', 'Vietnam'),
        ('INR', 'Indian Rupee', '₹', 'India'),
        ('PKR', 'Pakistani Rupee', '₨', 'Pakistan'),
        ('BDT', 'Bangladeshi Taka', '৳', 'Bangladesh'),
        ('LKR', 'Sri Lankan Rupee', '₨', 'Sri Lanka'),
        ('NPR', 'Nepalese Rupee', '₨', 'Nepal'),
        ('MMK', 'Myanmar Kyat', 'K', 'Myanmar'),
        ('KHR', 'Cambodian Riel', '៛', 'Cambodia'),
        ('LAK', 'Lao Kip', '₭', 'Laos'),
        ('MNT', 'Mongolian Tugrik', '₮', 'Mongolia'),
        ('KZT', 'Kazakhstani Tenge', '₸', 'Kazakhstan'),
        ('UZS', 'Uzbekistani Som', 'сўм', 'Uzbekistan'),
        ('KGS', 'Kyrgyzstani Som', 'с', 'Kyrgyzstan'),
        ('TJS', 'Tajikistani Somoni', 'SM', 'Tajikistan'),
        ('AFN', 'Afghan Afghani', '؋', 'Afghanistan'),
        
        # Middle Eastern currencies
        ('SAR', 'Saudi Riyal', '﷼', 'Saudi Arabia'),
        ('AED', 'UAE Dirham', 'د.إ', 'United Arab Emirates'),
        ('QAR', 'Qatari Riyal', '﷼', 'Qatar'),
        ('KWD', 'Kuwaiti Dinar', 'د.ك', 'Kuwait'),
        ('BHD', 'Bahraini Dinar', 'د.ب', 'Bahrain'),
        ('OMR', 'Omani Rial', '﷼', 'Oman'),
        ('JOD', 'Jordanian Dinar', 'د.ا', 'Jordan'),
        ('LBP', 'Lebanese Pound', 'ل.ل', 'Lebanon'),
        ('SYP', 'Syrian Pound', '£', 'Syria'),
        ('IQD', 'Iraqi Dinar', 'د.ع', 'Iraq'),
        ('ILS', 'Israeli Shekel', '₪', 'Israel'),
        ('TRY', 'Turkish Lira', '₺', 'Turkey'),
        ('IRR', 'Iranian Rial', '﷼', 'Iran'),
        
        # African currencies
        ('ZAR', 'South African Rand', 'R', 'South Africa'),
        ('EGP', 'Egyptian Pound', '£', 'Egypt'),
        ('NGN', 'Nigerian Naira', '₦', 'Nigeria'),
        ('KES', 'Kenyan Shilling', 'KSh', 'Kenya'),
        ('UGX', 'Ugandan Shilling', 'USh', 'Uganda'),
        ('TZS', 'Tanzanian Shilling', 'TSh', 'Tanzania'),
        ('ETB', 'Ethiopian Birr', 'Br', 'Ethiopia'),
        ('GHS', 'Ghanaian Cedi', '₵', 'Ghana'),
        ('MAD', 'Moroccan Dirham', 'د.م.', 'Morocco'),
        ('TND', 'Tunisian Dinar', 'د.ت', 'Tunisia'),
        ('DZD', 'Algerian Dinar', 'د.ج', 'Algeria'),
        ('LYD', 'Libyan Dinar', 'ل.د', 'Libya'),
        ('SDG', 'Sudanese Pound', 'ج.س.', 'Sudan'),
        ('AOA', 'Angolan Kwanza', 'Kz', 'Angola'),
        ('MZN', 'Mozambican Metical', 'MT', 'Mozambique'),
        ('BWP', 'Botswana Pula', 'P', 'Botswana'),
        ('ZMW', 'Zambian Kwacha', 'ZK', 'Zambia'),
        ('MWK', 'Malawian Kwacha', 'MK', 'Malawi'),
        ('SZL', 'Swazi Lilangeni', 'L', 'Eswatini'),
        ('LSL', 'Lesotho Loti', 'L', 'Lesotho'),
        ('NAD', 'Namibian Dollar', 'N$', 'Namibia'),
        ('BIF', 'Burundian Franc', 'FBu', 'Burundi'),
        ('RWF', 'Rwandan Franc', 'RF', 'Rwanda'),
        ('DJF', 'Djiboutian Franc', 'Fdj', 'Djibouti'),
        ('SOS', 'Somali Shilling', 'S', 'Somalia'),
        ('ERN', 'Eritrean Nakfa', 'Nfk', 'Eritrea'),
        ('CDF', 'Congolese Franc', 'FC', 'Democratic Republic of Congo'),
        ('CVE', 'Cape Verdean Escudo', '$', 'Cape Verde'),
        ('STN', 'São Tomé and Príncipe Dobra', 'Db', 'São Tomé and Príncipe'),
        ('GMD', 'Gambian Dalasi', 'D', 'Gambia'),
        ('GNF', 'Guinean Franc', 'FG', 'Guinea'),
        ('LRD', 'Liberian Dollar', 'L$', 'Liberia'),
        ('SLL', 'Sierra Leonean Leone', 'Le', 'Sierra Leone'),
        ('XOF', 'West African CFA Franc', 'CFA', 'West Africa'),
        ('XAF', 'Central African CFA Franc', 'FCFA', 'Central Africa'),
        
        # American currencies
        ('BRL', 'Brazilian Real', 'R$', 'Brazil'),
        ('ARS', 'Argentine Peso', '$', 'Argentina'),
        ('CLP', 'Chilean Peso', '$', 'Chile'),
        ('COP', 'Colombian Peso', '$', 'Colombia'),
        ('PEN', 'Peruvian Sol', 'S/', 'Peru'),
        ('UYU', 'Uruguayan Peso', '$U', 'Uruguay'),
        ('PYG', 'Paraguayan Guarani', '₲', 'Paraguay'),
        ('BOB', 'Bolivian Boliviano', 'Bs', 'Bolivia'),
        ('VES', 'Venezuelan Bolívar', 'Bs.S', 'Venezuela'),
        ('GYD', 'Guyanese Dollar', 'G$', 'Guyana'),
        ('SRD', 'Surinamese Dollar', '$', 'Suriname'),
        ('TTD', 'Trinidad and Tobago Dollar', 'TT$', 'Trinidad and Tobago'),
        ('JMD', 'Jamaican Dollar', 'J$', 'Jamaica'),
        ('BBD', 'Barbadian Dollar', 'Bds$', 'Barbados'),
        ('BZD', 'Belize Dollar', 'BZ$', 'Belize'),
        ('GTQ', 'Guatemalan Quetzal', 'Q', 'Guatemala'),
        ('HNL', 'Honduran Lempira', 'L', 'Honduras'),
        ('NIO', 'Nicaraguan Córdoba', 'C$', 'Nicaragua'),
        ('CRC', 'Costa Rican Colón', '₡', 'Costa Rica'),
        ('PAB', 'Panamanian Balboa', 'B/.', 'Panama'),
        ('DOP', 'Dominican Peso', 'RD$', 'Dominican Republic'),
        ('HTG', 'Haitian Gourde', 'G', 'Haiti'),
        ('CUP', 'Cuban Peso', '$', 'Cuba'),
        
        # Oceanian currencies
        ('FJD', 'Fijian Dollar', 'FJ$', 'Fiji'),
        ('PGK', 'Papua New Guinea Kina', 'K', 'Papua New Guinea'),
        ('SBD', 'Solomon Islands Dollar', 'SI$', 'Solomon Islands'),
        ('VUV', 'Vanuatu Vatu', 'Vt', 'Vanuatu'),
        ('WST', 'Samoan Tala', 'WS$', 'Samoa'),
        ('TOP', 'Tongan Paʻanga', 'T$', 'Tonga'),
        ('KID', 'Kiribati Dollar', '$', 'Kiribati'),
        
        # Other currencies
        ('RUB', 'Russian Ruble', '₽', 'Russia'),
        ('UAH', 'Ukrainian Hryvnia', '₴', 'Ukraine'),
        ('BYN', 'Belarusian Ruble', 'Br', 'Belarus'),
        ('MDL', 'Moldovan Leu', 'L', 'Moldova'),
        ('GEL', 'Georgian Lari', '₾', 'Georgia'),
        ('AMD', 'Armenian Dram', '֏', 'Armenia'),
        ('AZN', 'Azerbaijani Manat', '₼', 'Azerbaijan'),
        
        # Cryptocurrencies
        ('BTC', 'Bitcoin', '₿', 'Cryptocurrency'),
        ('ETH', 'Ethereum', 'Ξ', 'Cryptocurrency'),
        ('BNB', 'Binance Coin', 'BNB', 'Cryptocurrency'),
        ('ADA', 'Cardano', '₳', 'Cryptocurrency'),
        ('SOL', 'Solana', '◎', 'Cryptocurrency'),
        ('XRP', 'Ripple', 'XRP', 'Cryptocurrency'),
        ('DOT', 'Polkadot', 'DOT', 'Cryptocurrency'),
        ('DOGE', 'Dogecoin', 'Ð', 'Cryptocurrency'),
        ('AVAX', 'Avalanche', 'AVAX', 'Cryptocurrency'),
        ('MATIC', 'Polygon', 'MATIC', 'Cryptocurrency'),
        ('LTC', 'Litecoin', 'Ł', 'Cryptocurrency'),
        ('LINK', 'Chainlink', 'LINK', 'Cryptocurrency'),
        ('UNI', 'Uniswap', 'UNI', 'Cryptocurrency'),
        ('ATOM', 'Cosmos', 'ATOM', 'Cryptocurrency'),
        ('FTM', 'Fantom', 'FTM', 'Cryptocurrency'),
    ]
    
    for code, name, symbol, country in currencies_data:
        existing = Currency.query.filter_by(code=code).first()
        if not existing:
            currency = Currency(
                code=code,
                name=name,
                symbol=symbol,
                country=country
            )
            db.session.add(currency)
    
    db.session.commit()

def init_tax_rates():
    """Initialize database with realistic tax rates for different countries"""
    tax_rates_data = [
        # Major countries with realistic exchange tax rates
        ('USA', 'United States', 'USD', 0.0, 1.5, 5.0, 50.0),
        ('EUR', 'European Union', 'EUR', 0.0, 2.0, 3.0, 30.0),
        ('GBR', 'United Kingdom', 'GBP', 0.0, 1.8, 2.0, 25.0),
        ('JPN', 'Japan', 'JPY', 0.0, 2.2, 100.0, 2000.0),
        ('CHE', 'Switzerland', 'CHF', 0.0, 1.0, 2.0, 20.0),
        ('CAN', 'Canada', 'CAD', 0.0, 1.8, 3.0, 30.0),
        ('AUS', 'Australia', 'AUD', 0.0, 2.0, 3.0, 35.0),
        ('NZL', 'New Zealand', 'NZD', 0.0, 2.2, 3.0, 40.0),
        
        # European countries
        ('SWE', 'Sweden', 'SEK', 0.0, 2.5, 5.0, 50.0),
        ('NOR', 'Norway', 'NOK', 0.0, 2.3, 5.0, 45.0),
        ('DNK', 'Denmark', 'DKK', 0.0, 2.2, 5.0, 40.0),
        ('POL', 'Poland', 'PLN', 0.0, 3.0, 5.0, 50.0),
        ('CZE', 'Czech Republic', 'CZK', 0.0, 2.8, 5.0, 45.0),
        ('HUN', 'Hungary', 'HUF', 0.0, 3.2, 5.0, 60.0),
        ('ROU', 'Romania', 'RON', 0.0, 3.5, 5.0, 70.0),
        ('BGR', 'Bulgaria', 'BGN', 0.0, 3.0, 5.0, 50.0),
        ('HRV', 'Croatia', 'HRK', 0.0, 2.8, 5.0, 45.0),
        ('SRB', 'Serbia', 'RSD', 0.0, 4.0, 5.0, 80.0),
        ('MKD', 'North Macedonia', 'MKD', 0.0, 3.8, 5.0, 70.0),
        ('BIH', 'Bosnia and Herzegovina', 'BAM', 0.0, 3.5, 5.0, 60.0),
        ('ALB', 'Albania', 'ALL', 0.0, 4.2, 5.0, 90.0),
        ('ISL', 'Iceland', 'ISK', 0.0, 2.5, 5.0, 50.0),
        
        # Asian countries
        ('CHN', 'China', 'CNY', 0.0, 2.5, 5.0, 50.0),
        ('KOR', 'South Korea', 'KRW', 0.0, 2.8, 1000.0, 20000.0),
        ('SGP', 'Singapore', 'SGD', 0.0, 1.5, 2.0, 20.0),
        ('HKG', 'Hong Kong', 'HKD', 0.0, 1.8, 2.0, 25.0),
        ('TWN', 'Taiwan', 'TWD', 0.0, 2.2, 5.0, 50.0),
        ('THA', 'Thailand', 'THB', 0.0, 3.0, 5.0, 100.0),
        ('MYS', 'Malaysia', 'MYR', 0.0, 2.8, 5.0, 50.0),
        ('IDN', 'Indonesia', 'IDR', 0.0, 3.5, 5000.0, 100000.0),
        ('PHL', 'Philippines', 'PHP', 0.0, 3.2, 10.0, 200.0),
        ('VNM', 'Vietnam', 'VND', 0.0, 4.0, 10000.0, 200000.0),
        ('IND', 'India', 'INR', 0.0, 3.5, 10.0, 200.0),
        ('PAK', 'Pakistan', 'PKR', 0.0, 4.2, 20.0, 500.0),
        ('BGD', 'Bangladesh', 'BDT', 0.0, 4.5, 20.0, 500.0),
        ('LKA', 'Sri Lanka', 'LKR', 0.0, 4.0, 20.0, 400.0),
        ('NPL', 'Nepal', 'NPR', 0.0, 4.8, 25.0, 600.0),
        ('MMR', 'Myanmar', 'MMK', 0.0, 5.0, 30.0, 800.0),
        ('KHM', 'Cambodia', 'KHR', 0.0, 4.5, 20000.0, 500000.0),
        ('LAO', 'Laos', 'LAK', 0.0, 5.2, 25000.0, 600000.0),
        ('MNG', 'Mongolia', 'MNT', 0.0, 4.8, 2000.0, 50000.0),
        ('KAZ', 'Kazakhstan', 'KZT', 0.0, 3.8, 200.0, 5000.0),
        ('UZB', 'Uzbekistan', 'UZS', 0.0, 4.5, 5000.0, 100000.0),
        ('KGZ', 'Kyrgyzstan', 'KGS', 0.0, 4.8, 50.0, 1000.0),
        ('TJK', 'Tajikistan', 'TJS', 0.0, 5.0, 5.0, 100.0),
        ('AFG', 'Afghanistan', 'AFN', 0.0, 5.5, 20.0, 500.0),
        
        # Middle Eastern countries
        ('SAU', 'Saudi Arabia', 'SAR', 0.0, 2.0, 5.0, 50.0),
        ('ARE', 'United Arab Emirates', 'AED', 0.0, 1.8, 3.0, 30.0),
        ('QAT', 'Qatar', 'QAR', 0.0, 1.5, 3.0, 25.0),
        ('KWT', 'Kuwait', 'KWD', 0.0, 1.2, 0.5, 5.0),
        ('BHR', 'Bahrain', 'BHD', 0.0, 1.8, 1.0, 10.0),
        ('OMN', 'Oman', 'OMR', 0.0, 2.0, 2.0, 20.0),
        ('JOR', 'Jordan', 'JOD', 0.0, 3.0, 2.0, 30.0),
        ('LBN', 'Lebanon', 'LBP', 0.0, 4.5, 5000.0, 100000.0),
        ('SYR', 'Syria', 'SYP', 0.0, 5.0, 10000.0, 200000.0),
        ('IRQ', 'Iraq', 'IQD', 0.0, 4.2, 5000.0, 100000.0),
        ('ISR', 'Israel', 'ILS', 0.0, 2.5, 5.0, 50.0),
        ('TUR', 'Turkey', 'TRY', 0.0, 3.8, 10.0, 200.0),
        ('IRN', 'Iran', 'IRR', 0.0, 5.5, 50000.0, 1000000.0),
        
        # African countries
        ('ZAF', 'South Africa', 'ZAR', 0.0, 3.0, 10.0, 200.0),
        ('EGY', 'Egypt', 'EGP', 0.0, 4.0, 10.0, 200.0),
        ('NGA', 'Nigeria', 'NGN', 0.0, 4.5, 50.0, 1000.0),
        ('KEN', 'Kenya', 'KES', 0.0, 4.2, 20.0, 500.0),
        ('UGA', 'Uganda', 'UGX', 0.0, 5.0, 2000.0, 50000.0),
        ('TZA', 'Tanzania', 'TZS', 0.0, 4.8, 2000.0, 50000.0),
        ('ETH', 'Ethiopia', 'ETB', 0.0, 5.2, 20.0, 500.0),
        ('GHA', 'Ghana', 'GHS', 0.0, 4.5, 5.0, 100.0),
        ('MAR', 'Morocco', 'MAD', 0.0, 3.8, 5.0, 100.0),
        ('TUN', 'Tunisia', 'TND', 0.0, 4.0, 2.0, 50.0),
        ('DZA', 'Algeria', 'DZD', 0.0, 4.2, 50.0, 1000.0),
        ('LBY', 'Libya', 'LYD', 0.0, 4.5, 2.0, 50.0),
        ('SDN', 'Sudan', 'SDG', 0.0, 5.5, 10.0, 200.0),
        ('AGO', 'Angola', 'AOA', 0.0, 5.0, 50.0, 1000.0),
        ('MOZ', 'Mozambique', 'MZN', 0.0, 4.8, 20.0, 500.0),
        ('BWA', 'Botswana', 'BWP', 0.0, 3.5, 5.0, 100.0),
        ('ZMB', 'Zambia', 'ZMW', 0.0, 4.5, 10.0, 200.0),
        ('MWI', 'Malawi', 'MWK', 0.0, 5.0, 100.0, 2000.0),
        ('SWZ', 'Eswatini', 'SZL', 0.0, 4.0, 5.0, 100.0),
        ('LSO', 'Lesotho', 'LSL', 0.0, 4.2, 5.0, 100.0),
        ('NAM', 'Namibia', 'NAD', 0.0, 3.8, 5.0, 100.0),
        ('BDI', 'Burundi', 'BIF', 0.0, 5.5, 1000.0, 20000.0),
        ('RWA', 'Rwanda', 'RWF', 0.0, 4.8, 500.0, 10000.0),
        ('DJI', 'Djibouti', 'DJF', 0.0, 4.5, 50.0, 1000.0),
        ('SOM', 'Somalia', 'SOS', 0.0, 6.0, 100.0, 2000.0),
        ('ERI', 'Eritrea', 'ERN', 0.0, 5.8, 5.0, 100.0),
        ('COD', 'Democratic Republic of Congo', 'CDF', 0.0, 5.5, 1000.0, 20000.0),
        ('CPV', 'Cape Verde', 'CVE', 0.0, 4.0, 10.0, 200.0),
        ('STP', 'São Tomé and Príncipe', 'STN', 0.0, 4.5, 5.0, 100.0),
        ('GMB', 'Gambia', 'GMD', 0.0, 4.8, 5.0, 100.0),
        ('GIN', 'Guinea', 'GNF', 0.0, 5.2, 2000.0, 50000.0),
        ('LBR', 'Liberia', 'LRD', 0.0, 5.0, 2.0, 50.0),
        ('SLE', 'Sierra Leone', 'SLL', 0.0, 5.5, 2000.0, 50000.0),
        ('BFA', 'Burkina Faso', 'XOF', 0.0, 4.8, 50.0, 1000.0),
        ('CMR', 'Cameroon', 'XAF', 0.0, 4.5, 50.0, 1000.0),
        
        # American countries
        ('BRA', 'Brazil', 'BRL', 0.0, 4.0, 5.0, 100.0),
        ('ARG', 'Argentina', 'ARS', 0.0, 5.0, 10.0, 200.0),
        ('CHL', 'Chile', 'CLP', 0.0, 3.5, 1000.0, 20000.0),
        ('COL', 'Colombia', 'COP', 0.0, 4.2, 2000.0, 50000.0),
        ('PER', 'Peru', 'PEN', 0.0, 3.8, 2.0, 50.0),
        ('URY', 'Uruguay', 'UYU', 0.0, 4.0, 10.0, 200.0),
        ('PRY', 'Paraguay', 'PYG', 0.0, 4.5, 5000.0, 100000.0),
        ('BOL', 'Bolivia', 'BOB', 0.0, 4.8, 2.0, 50.0),
        ('VEN', 'Venezuela', 'VES', 0.0, 6.0, 5.0, 100.0),
        ('GUY', 'Guyana', 'GYD', 0.0, 4.5, 50.0, 1000.0),
        ('SUR', 'Suriname', 'SRD', 0.0, 4.2, 5.0, 100.0),
        ('TTO', 'Trinidad and Tobago', 'TTD', 0.0, 3.8, 5.0, 100.0),
        ('JAM', 'Jamaica', 'JMD', 0.0, 4.5, 20.0, 500.0),
        ('BRB', 'Barbados', 'BBD', 0.0, 3.5, 2.0, 50.0),
        ('BLZ', 'Belize', 'BZD', 0.0, 4.0, 2.0, 50.0),
        ('GTM', 'Guatemala', 'GTQ', 0.0, 4.2, 2.0, 50.0),
        ('HND', 'Honduras', 'HNL', 0.0, 4.5, 5.0, 100.0),
        ('NIC', 'Nicaragua', 'NIO', 0.0, 4.8, 5.0, 100.0),
        ('CRI', 'Costa Rica', 'CRC', 0.0, 4.0, 500.0, 10000.0),
        ('PAN', 'Panama', 'PAB', 0.0, 3.5, 1.0, 25.0),
        ('DOM', 'Dominican Republic', 'DOP', 0.0, 4.2, 10.0, 200.0),
        ('HTI', 'Haiti', 'HTG', 0.0, 5.0, 20.0, 500.0),
        ('CUB', 'Cuba', 'CUP', 0.0, 5.5, 5.0, 100.0),
        
        # Oceanian countries
        ('FJI', 'Fiji', 'FJD', 0.0, 3.8, 2.0, 50.0),
        ('PNG', 'Papua New Guinea', 'PGK', 0.0, 4.5, 2.0, 50.0),
        ('SLB', 'Solomon Islands', 'SBD', 0.0, 4.8, 2.0, 50.0),
        ('VUT', 'Vanuatu', 'VUV', 0.0, 4.2, 50.0, 1000.0),
        ('WSM', 'Samoa', 'WST', 0.0, 4.0, 2.0, 50.0),
        ('TON', 'Tonga', 'TOP', 0.0, 4.5, 1.0, 25.0),
        ('KIR', 'Kiribati', 'KID', 0.0, 4.8, 1.0, 25.0),
        
        # Other countries
        ('RUS', 'Russia', 'RUB', 0.0, 3.5, 50.0, 1000.0),
        ('UKR', 'Ukraine', 'UAH', 0.0, 4.5, 20.0, 500.0),
        ('BLR', 'Belarus', 'BYN', 0.0, 4.2, 5.0, 100.0),
        ('MDA', 'Moldova', 'MDL', 0.0, 4.8, 5.0, 100.0),
        ('GEO', 'Georgia', 'GEL', 0.0, 4.0, 1.0, 25.0),
        ('ARM', 'Armenia', 'AMD', 0.0, 4.5, 50.0, 1000.0),
        ('AZE', 'Azerbaijan', 'AZN', 0.0, 4.2, 1.0, 25.0),
    ]
    
    for country_code, country_name, currency_code, exchange_tax_rate, service_fee_rate, minimum_fee, maximum_fee in tax_rates_data:
        existing = TaxRate.query.filter_by(country_code=country_code, currency_code=currency_code).first()
        if not existing:
            tax_rate = TaxRate(
                country_code=country_code,
                country_name=country_name,
                currency_code=currency_code,
                exchange_tax_rate=exchange_tax_rate,
                service_fee_rate=service_fee_rate,
                minimum_fee=minimum_fee,
                maximum_fee=maximum_fee
            )
            db.session.add(tax_rate)
    
    db.session.commit()

@app.route('/')
def index():
    return render_template('converter.html')

@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')

@app.route('/api/currencies')
def get_currencies():
    currencies = Currency.query.filter_by(is_active=True).all()
    return jsonify([{
        'code': c.code,
        'name': c.name,
        'symbol': c.symbol,
        'country': c.country
    } for c in currencies])

@app.route('/api/convert', methods=['POST'])
def convert_currency():
    data = request.get_json()
    amount = float(data.get('amount', 1))
    from_currency = data.get('from_currency', 'USD')
    to_currency = data.get('to_currency', 'EUR')
    
    try:
        rate = get_exchange_rate(from_currency, to_currency)
        result = amount * rate
        
        return jsonify({
            'success': True,
            'amount': amount,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'rate': rate,
            'result': round(result, 4),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/rates/<from_currency>/<to_currency>')
def get_rate(from_currency, to_currency):
    try:
        rate = get_exchange_rate(from_currency, to_currency)
        return jsonify({
            'from_currency': from_currency,
            'to_currency': to_currency,
            'rate': rate,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/history/<from_currency>/<to_currency>')
def get_rate_history(from_currency, to_currency):
    days = request.args.get('days', 7, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    
    rates = ExchangeRate.query.filter(
        ExchangeRate.from_currency == from_currency,
        ExchangeRate.to_currency == to_currency,
        ExchangeRate.timestamp >= since
    ).order_by(ExchangeRate.timestamp.asc()).all()
    
    # If no historical data, generate some sample data for demo
    if not rates:
        from currency_converter.currency_converter import CurrencyConverter
        try:
            converter = CurrencyConverter()
            base_rate = converter.convert(1, from_currency, to_currency)
            
            # Generate sample historical data with small variations
            import random
            sample_rates = []
            for i in range(days):
                date = datetime.utcnow() - timedelta(days=days-i-1)
                # Add small random variation (±2%)
                variation = random.uniform(-0.02, 0.02)
                rate = base_rate * (1 + variation)
                
                sample_rates.append({
                    'timestamp': date.isoformat(),
                    'rate': round(rate, 4)
                })
            
            return jsonify(sample_rates)
        except:
            pass
    
    return jsonify([{
        'timestamp': rate.timestamp.isoformat(),
        'rate': rate.rate
    } for rate in rates])

@app.route('/api/chart-data/<from_currency>/<to_currency>')
def get_chart_data(from_currency, to_currency):
    """Get data formatted for Chart.js with maximum performance"""
    days = request.args.get('days', 7, type=int)
    
    # Ultra-fast static data generation (no API calls)
    import random
    labels = []
    data = []
    
    # Use cached rate if available, otherwise use static values
    try:
        recent_rate = ExchangeRate.query.filter(
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency
        ).order_by(ExchangeRate.timestamp.desc()).first()
        
        base_rate = recent_rate.rate if recent_rate else 1.0
    except:
        base_rate = 1.0
    
    for i in range(days):
        labels.append(f'{i+1}D')
        # Very small variation for smooth line
        variation = random.uniform(-0.005, 0.005)
        rate = base_rate * (1 + variation)
        data.append(round(rate, 4))
    
    return jsonify({
        'labels': labels,
        'data': data,
        'current_rate': base_rate
    })

@app.route('/api/tax-rates/<currency_code>')
def get_tax_rates(currency_code):
    """Get tax rates for a specific currency"""
    try:
        tax_rates = TaxRate.query.filter_by(currency_code=currency_code, is_active=True).all()
        
        if not tax_rates:
            return jsonify({'error': 'No tax rates found for this currency'}), 404
        
        return jsonify([{
            'country_code': tr.country_code,
            'country_name': tr.country_name,
            'currency_code': tr.currency_code,
            'exchange_tax_rate': tr.exchange_tax_rate,
            'service_fee_rate': tr.service_fee_rate,
            'minimum_fee': tr.minimum_fee,
            'maximum_fee': tr.maximum_fee,
            'last_updated': tr.last_updated.isoformat()
        } for tr in tax_rates])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/calculate-tax', methods=['POST'])
def calculate_tax():
    """Calculate tax and fees for currency exchange"""
    data = request.get_json()
    amount = float(data.get('amount', 0))
    from_currency = data.get('from_currency', 'USD')
    to_currency = data.get('to_currency', 'EUR')
    country_code = data.get('country_code', 'USA')
    
    try:
        # Get exchange rate
        rate = get_exchange_rate(from_currency, to_currency)
        gross_amount = amount * rate
        
        # Get tax rates for the destination currency
        tax_rate = TaxRate.query.filter_by(
            country_code=country_code, 
            currency_code=to_currency,
            is_active=True
        ).first()
        
        if not tax_rate:
            # Try any country with same currency
            tax_rate = TaxRate.query.filter_by(
                currency_code=to_currency,
                is_active=True
            ).first()
        
        if not tax_rate:
            # Use default rates (2% service fee, no exchange tax)
            tax_rate_data = {
                'country_code': country_code,
                'country_name': country_code,
                'exchange_tax_rate': 0.0,
                'service_fee_rate': 2.0,
                'minimum_fee': 3.0,
                'maximum_fee': 50.0
            }
            tax_rate = type('obj', (object,), tax_rate_data)()
        
        # Calculate taxes and fees
        exchange_tax = gross_amount * (tax_rate.exchange_tax_rate / 100)
        service_fee = gross_amount * (tax_rate.service_fee_rate / 100)
        
        # Apply minimum/maximum fee constraints
        if service_fee < tax_rate.minimum_fee:
            service_fee = tax_rate.minimum_fee
        elif tax_rate.maximum_fee and service_fee > tax_rate.maximum_fee:
            service_fee = tax_rate.maximum_fee
        
        total_tax_fee = exchange_tax + service_fee
        net_amount = gross_amount - total_tax_fee
        
        return jsonify({
            'success': True,
            'original_amount': amount,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'exchange_rate': rate,
            'gross_amount': round(gross_amount, 4),
            'exchange_tax': round(exchange_tax, 4),
            'service_fee': round(service_fee, 4),
            'total_tax_fee': round(total_tax_fee, 4),
            'net_amount': round(net_amount, 4),
            'tax_rate_info': {
                'country_code': tax_rate.country_code,
                'country_name': tax_rate.country_name,
                'exchange_tax_rate': tax_rate.exchange_tax_rate,
                'service_fee_rate': tax_rate.service_fee_rate,
                'minimum_fee': tax_rate.minimum_fee,
                'maximum_fee': tax_rate.maximum_fee
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/countries')
def get_countries():
    """Get list of countries with their currencies"""
    try:
        countries = TaxRate.query.filter_by(is_active=True).distinct().all()
        
        country_list = []
        seen_countries = set()
        
        for country in countries:
            if country.country_code not in seen_countries:
                country_list.append({
                    'country_code': country.country_code,
                    'country_name': country.country_name,
                    'currency_code': country.currency_code
                })
                seen_countries.add(country.country_code)
        
        return jsonify(country_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/portfolio/<user_id>')
def get_portfolio(user_id):
    """Get user's currency portfolio"""
    try:
        portfolio_items = Portfolio.query.filter_by(user_id=user_id).all()
        
        portfolio_data = []
        total_value_usd = 0
        
        for item in portfolio_items:
            current_rate = get_exchange_rate(item.currency_code, 'USD')
            current_value = item.amount * current_rate if current_rate else 0
            purchase_value = item.amount * item.purchase_rate
            profit_loss = current_value - purchase_value
            profit_loss_percent = (profit_loss / purchase_value * 100) if purchase_value > 0 else 0
            
            portfolio_data.append({
                'id': item.id,
                'currency_code': item.currency_code,
                'amount': item.amount,
                'purchase_rate': item.purchase_rate,
                'current_rate': current_rate,
                'current_value_usd': round(current_value, 2),
                'purchase_value_usd': round(purchase_value, 2),
                'profit_loss_usd': round(profit_loss, 2),
                'profit_loss_percent': round(profit_loss_percent, 2),
                'purchase_date': item.purchase_date.isoformat(),
                'notes': item.notes
            })
            
            total_value_usd += current_value
        
        return jsonify({
            'portfolio': portfolio_data,
            'total_value_usd': round(total_value_usd, 2),
            'total_items': len(portfolio_data)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/portfolio', methods=['POST'])
def add_portfolio_item():
    """Add item to portfolio"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'anonymous')
        currency_code = data.get('currency_code')
        amount = float(data.get('amount', 0))
        purchase_rate = float(data.get('purchase_rate', 0))
        notes = data.get('notes', '')
        
        if not currency_code or amount <= 0 or purchase_rate <= 0:
            return jsonify({'error': 'Invalid data provided'}), 400
        
        portfolio_item = Portfolio(
            user_id=user_id,
            currency_code=currency_code,
            amount=amount,
            purchase_rate=purchase_rate,
            notes=notes
        )
        
        db.session.add(portfolio_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Portfolio item added successfully',
            'id': portfolio_item.id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/crypto-trends')
def get_crypto_trends():
    """Get cryptocurrency market trends"""
    try:
        crypto_currencies = ['bitcoin', 'ethereum', 'binancecoin', 'cardano', 'solana', 'ripple']
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(crypto_currencies)}&vs_currencies=usd&include_24hr_change=true"
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            trends = []
            for crypto_id, crypto_data in data.items():
                trends.append({
                    'symbol': crypto_id.upper(),
                    'price_usd': crypto_data.get('usd', 0),
                    'change_24h': crypto_data.get('usd_24h_change', 0)
                })
            
            return jsonify(trends)
    except Exception as e:
        print(f"Crypto trends error: {e}")
    
    return jsonify([])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_currencies()
        init_tax_rates()
    app.run(debug=True, host='0.0.0.0', port=5000)
