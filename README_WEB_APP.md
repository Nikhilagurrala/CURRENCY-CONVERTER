# Real-Time Currency Converter Web Application

A modern, responsive web application for real-time currency conversion with support for 100+ currencies worldwide.

## Features

- 🌍 **100+ Currencies**: Support for major and minor currencies from around the world
- ⚡ **Real-Time Rates**: Live exchange rates from ExchangeRate-API
- 💾 **Caching**: Intelligent caching to reduce API calls and improve performance
- 📱 **Responsive Design**: Beautiful, mobile-friendly interface
- ⭐ **Favorites**: Save your frequently used currencies
- 📊 **Statistics**: Track conversion history and usage
- 🔄 **Auto-Update**: Real-time rate updates
- 🎨 **Modern UI**: Clean, professional design with smooth animations

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setup

1. **Clone or download the project**
   ```bash
   cd currencyconverter
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   EXCHANGE_API_KEY=your_exchangerate_api_key_here
   FLASK_SECRET_KEY=your_secret_key_here
   ```

4. **Get API Key**
   - Visit [ExchangeRate-API](https://www.exchangerate-api.com/)
   - Sign up for a free account
   - Get your API key
   - Add it to your `.env` file

5. **Initialize the database**
   ```bash
   python app.py
   ```
   This will create the SQLite database and populate it with 100+ currencies.

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Open your browser**
   Navigate to `http://localhost:5000`

## API Endpoints

### Get All Currencies
```
GET /api/currencies
```
Returns list of all supported currencies.

### Convert Currency
```
POST /api/convert
Content-Type: application/json

{
    "amount": 100,
    "from_currency": "USD",
    "to_currency": "EUR"
}
```

### Get Exchange Rate
```
GET /api/rates/{from_currency}/{to_currency}
```

### Get Rate History
```
GET /api/history/{from_currency}/{to_currency}?hours=24
```

## Supported Currencies

The application supports 100+ currencies including:

### Major Currencies
- USD (US Dollar)
- EUR (Euro)
- GBP (British Pound)
- JPY (Japanese Yen)
- CHF (Swiss Franc)
- CAD (Canadian Dollar)
- AUD (Australian Dollar)

### European Currencies
- SEK, NOK, DKK, PLN, CZK, HUF, RON, BGN, HRK, RSD, MKD, BAM, ALL, ISK

### Asian Currencies
- CNY, KRW, SGD, HKD, TWD, THB, MYR, IDR, PHP, VND, INR, PKR, BDT, LKR, NPR, MMK, KHR, LAK, MNT, KZT, UZS, KGS, TJS, AFN

### Middle Eastern Currencies
- SAR, AED, QAR, KWD, BHD, OMR, JOD, LBP, SYP, IQD, ILS, TRY, IRR

### African Currencies
- ZAR, EGP, NGN, KES, UGX, TZS, ETB, GHS, MAD, TND, DZD, LYD, SDG, AOA, MZN, BWP, ZMW, MWK, SZL, LSL, NAD, BIF, RWF, DJF, SOS, ERN, CDF, CVE, STN, GMD, GNF, LRD, SLL, XOF, XAF

### American Currencies
- BRL, ARS, CLP, COP, PEN, UYU, PYG, BOB, VES, GYD, SRD, TTD, JMD, BBD, BZD, GTQ, HNL, NIO, CRC, PAB, DOP, HTG, CUP

### Oceanian Currencies
- FJD, PGK, SBD, VUV, WST, TOP, KID

### Other Currencies
- RUB, UAH, BYN, MDL, GEL, AMD, AZN

## Configuration

### Environment Variables
- `EXCHANGE_API_KEY`: Your ExchangeRate-API key
- `FLASK_SECRET_KEY`: Secret key for Flask sessions
- `SQLALCHEMY_DATABASE_URI`: Database connection string (default: SQLite)

### Database
The application uses SQLite by default, but can be configured to use PostgreSQL, MySQL, or other databases supported by SQLAlchemy.

## Deployment

### Local Development
```bash
python app.py
```

### Production with Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker Deployment
Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## Features in Detail

### Real-Time Updates
- Rates are cached for 1 hour to reduce API calls
- Automatic fallback to last known rates if API is unavailable
- Background rate updates

### User Experience
- Responsive design works on all devices
- Smooth animations and transitions
- Error handling with user-friendly messages
- Loading states and progress indicators

### Performance
- Efficient database queries with proper indexing
- Client-side caching of currency data
- Debounced input to prevent excessive API calls
- Optimized asset loading

## Troubleshooting

### Common Issues

1. **API Key Issues**
   - Ensure your ExchangeRate-API key is valid
   - Check if you've exceeded API rate limits
   - Verify the key is correctly set in `.env`

2. **Database Issues**
   - Delete `currency_tracker.db` and restart the app
   - Check file permissions in the project directory

3. **Port Issues**
   - Change the port in `app.py` if 5000 is occupied
   - Use `app.run(debug=True, port=5001)`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For support, please open an issue in the project repository or contact the development team.
