# 💱 Advanced Currency Converter & Portfolio Tracker

A comprehensive currency conversion application with real-time exchange rates, tax calculations, cryptocurrency support, and portfolio tracking features.

## 🌟 Key Features

### 💰 Core Currency Conversion
- **Real-time Exchange Rates**: Live currency conversion using ExchangeRate-API
- **Tax & Fee Calculator**: Accurate calculation of exchange taxes and service fees by country
- **Multi-Currency Support**: Support for 50+ traditional currencies
- **Interactive Charts**: Visual representation of currency trends over time

### 🚀 Unique Differentiating Features

#### 🪙 Cryptocurrency Integration
- **15+ Major Cryptocurrencies**: Bitcoin, Ethereum, Binance Coin, Cardano, Solana, and more
- **Real-time Crypto Rates**: Live cryptocurrency prices via CoinGecko API
- **Crypto-to-Fiat Conversion**: Seamless conversion between crypto and traditional currencies
- **Crypto Market Trends**: Live 24-hour price changes and market data

#### 📊 Portfolio Tracker
- **Multi-Currency Portfolio**: Track investments across different currencies and cryptocurrencies
- **Profit/Loss Analysis**: Real-time P&L calculations with percentage changes
- **Purchase History**: Track when and at what rate you bought currencies
- **Portfolio Valuation**: Total portfolio value in USD with individual asset breakdown

#### 🌍 Global Tax System
- **Country-Specific Tax Rates**: Accurate tax calculations for 100+ countries
- **Exchange Location Selection**: Choose your exchange location for precise tax calculations
- **Fee Structure**: Minimum/maximum fee constraints and service fee calculations
- **Tax Breakdown**: Detailed breakdown of all fees and taxes applied

#### 📈 Advanced Analytics
- **Historical Rate Charts**: 7, 14, and 30-day currency trend analysis
- **Interactive Visualizations**: Chart.js powered charts for better data understanding
- **Real-time Updates**: Live rate updates every hour for accuracy
- **Trend Analysis**: Visual representation of currency performance over time

## 🛠️ Technology Stack

### Backend
- **Flask**: Python web framework for API development
- **SQLAlchemy**: ORM for database management
- **SQLite**: Lightweight database for data storage
- **Flask-Migrate**: Database migration management

### Frontend
- **HTML5/CSS3**: Modern responsive design
- **JavaScript (ES6+)**: Interactive frontend functionality
- **Chart.js**: Data visualization and charting
- **Bootstrap 5**: Responsive UI framework
- **Font Awesome**: Icon library

### APIs & External Services
- **ExchangeRate-API**: Real-time currency exchange rates
- **CoinGecko API**: Cryptocurrency market data
- **RESTful Architecture**: Clean API design for scalability

## 📁 Project Structure

```
currencyconverter/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/
│   ├── converter.html     # Main conversion page
│   ├── results.html      # Results and analysis page
│   └── portfolio.html    # Portfolio tracking page
├── static/               # Static assets (if any)
└── README.md             # Project documentation
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Kausiq000/currencyconverter.git
   cd currencyconverter
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the application**
   - Open your browser and navigate to `http://localhost:5000`
   - The application will automatically initialize the database and load currency data

## 📖 Usage Guide

### 💱 Currency Conversion
1. **Select Currencies**: Choose source and target currencies from the dropdown
2. **Enter Amount**: Input the amount you want to convert
3. **Choose Exchange Location**: Select your country for accurate tax calculations
4. **Convert**: Click convert to see real-time rates and tax breakdown
5. **View Results**: See detailed results with charts and analysis

### 📊 Portfolio Tracking
1. **Navigate to Portfolio**: Click the Portfolio tab
2. **Add Holdings**: Enter currency, amount, and purchase rate
3. **Track Performance**: View real-time P&L and portfolio value
4. **Monitor Trends**: Check crypto market trends and currency performance

### 🌍 Tax Calculations
- **Automatic Detection**: System automatically applies relevant tax rates
- **Country-Specific**: Different tax rates for different countries
- **Fee Breakdown**: Detailed breakdown of all fees and taxes
- **Net Amount**: Clear display of final amount after all deductions

## 🔧 API Endpoints

### Core Conversion
- `GET /api/currencies` - Get list of supported currencies
- `GET /api/rates/{from}/{to}` - Get exchange rate between currencies
- `POST /api/calculate-tax` - Calculate taxes and fees for conversion

### Cryptocurrency
- `GET /api/crypto-trends` - Get cryptocurrency market trends
- `GET /api/rates/{crypto}/{fiat}` - Get crypto-to-fiat rates

### Portfolio Management
- `GET /api/portfolio/{user_id}` - Get user portfolio
- `POST /api/portfolio` - Add item to portfolio

### Tax & Countries
- `GET /api/countries` - Get list of countries with tax rates
- `GET /api/tax-rates/{currency}` - Get tax rates for currency

## 🎨 Design Features

### 🌙 Modern UI/UX
- **Dark Theme**: Sleek black and blue gradient design
- **Neon Accents**: Bright blue accents for modern appeal
- **Responsive Design**: Works perfectly on all devices
- **Smooth Animations**: Fluid transitions and hover effects

### 📱 Mobile-First
- **Responsive Layout**: Optimized for mobile devices
- **Touch-Friendly**: Large buttons and easy navigation
- **Fast Loading**: Optimized for quick page loads

## 🔒 Security & Privacy

- **No Personal Data Storage**: No sensitive user information stored
- **Local Storage**: User preferences stored locally in browser
- **API Security**: Secure API endpoints with error handling
- **Data Validation**: Input validation and sanitization

## 🚀 Deployment

### Local Development
```bash
python app.py
```

### Production Deployment
1. Set up a production WSGI server (Gunicorn, uWSGI)
2. Configure environment variables
3. Set up reverse proxy (Nginx)
4. Enable HTTPS for secure connections

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **ExchangeRate-API** for reliable currency data
- **CoinGecko** for cryptocurrency market data
- **Chart.js** for beautiful data visualizations
- **Bootstrap** for responsive UI components
- **Font Awesome** for comprehensive icon library

## 📞 Support

For support, email support@currencyconverter.com or create an issue in the GitHub repository.

## 🔮 Future Enhancements

- [ ] Machine Learning price predictions
- [ ] Currency news feed integration
- [ ] Advanced portfolio analytics
- [ ] Mobile app development
- [ ] Multi-language support
- [ ] Advanced charting tools
- [ ] Currency alerts and notifications
- [ ] Historical data analysis

---

